from control_center.models import DiscussionStatus, WorkItemStatus, WorkflowRunStatus
from control_center.services import WorkflowScheduler
from control_center.models.hierarchy import now_utc
from control_center.models import ArtifactType


def test_scheduler_supports_two_parallel_and_one_join() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")

    first = scheduler.add_workitem(run.id, role="module-dev", module_key="auth")
    second = scheduler.add_workitem(run.id, role="module-dev", module_key="billing")
    join = scheduler.add_workitem(
        run.id,
        role="qa-test",
        module_key="integration",
        depends_on=[first.id, second.id],
    )

    first_ready = scheduler.tick(run.id)
    assert {item.id for item in first_ready} == {first.id, second.id}
    assert scheduler.get_workitem(join.id).status == WorkItemStatus.PENDING

    scheduler.start_workitem(first.id)
    scheduler.start_workitem(second.id)
    scheduler.complete_workitem(first.id, success=True)
    scheduler.tick(run.id)
    assert scheduler.get_workitem(join.id).status == WorkItemStatus.PENDING

    scheduler.complete_workitem(second.id, success=True)
    second_ready = scheduler.tick(run.id)
    assert [item.id for item in second_ready] == [join.id]
    assert scheduler.get_run(run.id).status == WorkflowRunStatus.RUNNING


def test_add_workitem_rejects_unknown_dependency() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")

    with_validation_error = False
    try:
        scheduler.add_workitem(
            run.id,
            role="qa-test",
            depends_on=["wi_missing"],
        )
    except ValueError:
        with_validation_error = True

    assert with_validation_error


def test_run_is_failed_when_any_workitem_failed() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(run.id, role="module-dev")

    scheduler.tick(run.id)
    scheduler.start_workitem(item.id)
    scheduler.complete_workitem(item.id, success=False)

    assert scheduler.get_run(run.id).status == WorkflowRunStatus.FAILED


def test_run_is_succeeded_when_all_workitems_succeeded() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(run.id, role="module-dev")

    scheduler.tick(run.id)
    scheduler.start_workitem(item.id)
    scheduler.complete_workitem(item.id, success=True)

    assert scheduler.get_run(run.id).status == WorkflowRunStatus.SUCCEEDED


def test_start_requires_ready_status() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(run.id, role="module-dev")

    with_validation_error = False
    try:
        scheduler.start_workitem(item.id)
    except ValueError:
        with_validation_error = True

    assert with_validation_error


def test_discussion_flow_blocks_and_resolves_workitem() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(run.id, role="module-dev")

    scheduler.tick(run.id)
    scheduler.start_workitem(item.id)
    session = scheduler.mark_needs_discussion(
        item.id,
        question="Need architecture decision",
        options=["a", "b"],
        fingerprint="fp-1",
    )

    assert session.status == DiscussionStatus.OPEN
    assert scheduler.get_workitem(item.id).status == WorkItemStatus.NEEDS_DISCUSSION
    assert scheduler.get_run(run.id).status == WorkflowRunStatus.BLOCKED

    resolved = scheduler.resolve_discussion(
        item.id,
        decision="choose a",
        resolved_by_role="chief-architect",
    )
    assert resolved.status == DiscussionStatus.RESOLVED
    assert scheduler.get_workitem(item.id).status == WorkItemStatus.READY


def test_discussion_budget_exhausted_marks_workitem_failed() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(run.id, role="module-dev", discussion_budget=0)
    scheduler.tick(run.id)
    scheduler.start_workitem(item.id)

    session = scheduler.mark_needs_discussion(
        item.id,
        question="Need discussion",
        fingerprint="fp-budget",
    )
    assert session.status == DiscussionStatus.EXHAUSTED
    assert scheduler.get_workitem(item.id).status == WorkItemStatus.FAILED
    assert scheduler.get_run(run.id).status == WorkflowRunStatus.FAILED


def test_discussion_loop_guard_marks_workitem_failed() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(run.id, role="module-dev", discussion_budget=3)
    scheduler.tick(run.id)
    scheduler.start_workitem(item.id)

    first = scheduler.mark_needs_discussion(
        item.id,
        question="Need discussion",
        fingerprint="fp-loop",
    )
    assert first.status == DiscussionStatus.OPEN
    scheduler.resolve_discussion(
        item.id,
        decision="temporary decision",
        resolved_by_role="chief-architect",
    )
    scheduler.start_workitem(item.id)
    second = scheduler.mark_needs_discussion(
        item.id,
        question="Need discussion again",
        fingerprint="fp-loop",
    )
    assert second.status == DiscussionStatus.EXHAUSTED
    assert scheduler.get_workitem(item.id).status == WorkItemStatus.FAILED


def test_discussion_timeout_marks_workitem_failed_on_resolve() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(
        run.id,
        role="module-dev",
        discussion_timeout_seconds=1,
    )
    scheduler.tick(run.id)
    scheduler.start_workitem(item.id)
    session = scheduler.mark_needs_discussion(
        item.id,
        question="Need discussion",
        fingerprint="fp-timeout",
    )
    session.created_at = now_utc().replace(year=2000)

    result = scheduler.resolve_discussion(
        item.id,
        decision="late decision",
        resolved_by_role="chief-architect",
    )
    assert result.status == DiscussionStatus.TIMEOUT
    assert scheduler.get_workitem(item.id).status == WorkItemStatus.FAILED


def test_waiting_approval_flow() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(
        run.id,
        role="release-manager",
        requires_approval=True,
    )

    ready = scheduler.tick(run.id)
    assert ready == []
    assert scheduler.get_workitem(item.id).status == WorkItemStatus.WAITING_APPROVAL
    assert scheduler.get_run(run.id).status == WorkflowRunStatus.WAITING_APPROVAL

    approved = scheduler.approve_workitem(item.id, approved_by="owner")
    assert approved.status == WorkItemStatus.READY
    assert approved.metadata["approved_by"] == "owner"


def test_artifact_create_and_list() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_alpha")
    item = scheduler.add_workitem(run.id, role="acceptance")

    artifact = scheduler.create_artifact(
        item.id,
        artifact_type=ArtifactType.ACCEPTANCE_REPORT,
        title="Acceptance report",
        uri_or_path="artifacts/acceptance.md",
        created_by="acceptance",
    )
    assert artifact.artifact_type == ArtifactType.ACCEPTANCE_REPORT

    artifacts = scheduler.list_artifacts(run.id)
    assert len(artifacts) == 1


def test_interrupt_run_marks_non_terminal_items_skipped_and_run_canceled() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_interrupt")
    item = scheduler.add_workitem(run.id, role="module-dev")

    scheduler.tick(run.id)
    scheduler.start_workitem(item.id)

    (
        previous_status,
        run_status,
        interrupt_applied,
        skipped_workitem_ids,
    ) = scheduler.interrupt_run(
        run.id,
        requested_by="owner",
        reason="manual stop",
    )
    assert previous_status == WorkflowRunStatus.RUNNING
    assert run_status == WorkflowRunStatus.CANCELED
    assert interrupt_applied is True
    assert skipped_workitem_ids == [item.id]

    interrupted_item = scheduler.get_workitem(item.id)
    assert interrupted_item.status == WorkItemStatus.SKIPPED
    assert interrupted_item.metadata["skip_reason"] == "workflow_run_interrupted"
    assert interrupted_item.metadata["interrupt_requested_by"] == "owner"
    assert interrupted_item.metadata["interrupt_reason"] == "manual stop"
    assert scheduler.get_run(run.id).status == WorkflowRunStatus.CANCELED


def test_interrupt_run_is_idempotent_when_already_canceled() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_interrupt_idempotent")
    item = scheduler.add_workitem(run.id, role="module-dev")
    scheduler.tick(run.id)

    scheduler.interrupt_run(run.id, reason="first stop")
    (
        previous_status,
        run_status,
        interrupt_applied,
        skipped_workitem_ids,
    ) = scheduler.interrupt_run(run.id, reason="second stop")

    assert previous_status == WorkflowRunStatus.CANCELED
    assert run_status == WorkflowRunStatus.CANCELED
    assert interrupt_applied is False
    assert skipped_workitem_ids == []
    assert scheduler.get_workitem(item.id).status == WorkItemStatus.SKIPPED


def test_restart_run_creates_new_run_and_copies_decomposition() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_restart", requested_by="owner")
    scheduler.add_workitem(run.id, role="module-dev")
    scheduler.interrupt_run(run.id, requested_by="owner", reason="stop for restart")
    run.metadata["chief_decomposition"] = {
        "modules": ["market-data"],
        "module_task_packages": {"market-data": [{"role": "module-dev"}]},
    }
    scheduler.persist_run(run.id)

    restarted_run, copied = scheduler.restart_run(
        run.id,
        requested_by="owner",
        reason="continue execution",
        copy_decomposition=True,
    )
    assert restarted_run.id != run.id
    assert restarted_run.project_id == run.project_id
    assert restarted_run.status == WorkflowRunStatus.RUNNING
    assert copied is True
    assert restarted_run.metadata["restart"]["source_run_id"] == run.id
    assert restarted_run.metadata["restart"]["requested_by"] == "owner"
    assert restarted_run.metadata["restart"]["reason"] == "continue execution"
    assert restarted_run.metadata["restart"]["copied_decomposition"] is True
    assert restarted_run.metadata["chief_decomposition"]["modules"] == ["market-data"]
    assert scheduler.list_workitems(restarted_run.id) == []


def test_restart_run_rejects_non_terminal_source() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj_restart_invalid")
    scheduler.add_workitem(run.id, role="module-dev")

    with_validation_error = False
    try:
        scheduler.restart_run(run.id)
    except ValueError:
        with_validation_error = True

    assert with_validation_error
