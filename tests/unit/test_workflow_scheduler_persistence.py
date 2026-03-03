from pathlib import Path

from control_center.models import (
    ArtifactType,
    DiscussionStatus,
    GateType,
    WorkItemStatus,
    WorkflowRunStatus,
)
from control_center.services import SQLiteStateStore, WorkflowScheduler


def _build_scheduler(db_path: Path) -> WorkflowScheduler:
    return WorkflowScheduler(state_store=SQLiteStateStore(str(db_path)))


def test_scheduler_restores_v3_entities_after_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow-state.db"
    scheduler = _build_scheduler(db_path)

    run = scheduler.create_run(project_id="proj-persist", requested_by="owner")
    module_dev = scheduler.add_workitem(run.id, role="module-dev", module_key="auth")
    release = scheduler.add_workitem(
        run.id,
        role="release-manager",
        module_key="global",
        depends_on=[module_dev.id],
        requires_approval=True,
    )

    ready = scheduler.tick(run.id)
    assert [item.id for item in ready] == [module_dev.id]
    scheduler.start_workitem(module_dev.id)
    discussion = scheduler.mark_needs_discussion(
        module_dev.id,
        question="Need direction",
        options=["ship", "hold"],
        fingerprint="persist-fp",
    )
    assert discussion.status == DiscussionStatus.OPEN
    scheduler.resolve_discussion(
        module_dev.id,
        decision="ship",
        resolved_by_role="chief-architect",
    )
    scheduler.start_workitem(module_dev.id)
    scheduler.complete_workitem(module_dev.id, success=True)

    scheduler.tick(run.id)
    assert scheduler.get_workitem(release.id).status == WorkItemStatus.WAITING_APPROVAL
    scheduler.approve_workitem(release.id, approved_by="release-owner")
    scheduler.start_workitem(release.id)
    scheduler.complete_workitem(release.id, success=True)

    first_gate = scheduler.create_gate_check(
        module_dev.id,
        gate_type=GateType.TEST,
        passed=True,
        summary="tests passed",
        executed_by="qa-test",
    )
    first_artifact = scheduler.create_artifact(
        module_dev.id,
        artifact_type=ArtifactType.TEST_REPORT,
        title="Module test report",
        uri_or_path="artifacts/module-dev/test-report.md",
        created_by="qa-test",
    )

    restored = _build_scheduler(db_path)

    restored_run = restored.get_run(run.id)
    assert restored_run.status == WorkflowRunStatus.SUCCEEDED

    restored_items = restored.list_workitems(run.id)
    assert [item.id for item in restored_items] == [module_dev.id, release.id]
    assert all(item.status == WorkItemStatus.SUCCEEDED for item in restored_items)

    restored_discussions = restored.list_discussions(module_dev.id)
    assert len(restored_discussions) == 1
    assert restored_discussions[0].status == DiscussionStatus.RESOLVED
    assert restored_discussions[0].decision == "ship"

    restored_gates = restored.list_gate_checks(run.id)
    assert len(restored_gates) == 1
    assert restored_gates[0].id == first_gate.id

    restored_artifacts = restored.list_artifacts(run.id)
    assert len(restored_artifacts) == 1
    assert restored_artifacts[0].id == first_artifact.id

    second_gate = restored.create_gate_check(
        module_dev.id,
        gate_type=GateType.SECURITY,
        passed=False,
        summary="security findings",
        executed_by="security-review",
    )
    assert second_gate.attempt == 2

    restored.create_artifact(
        release.id,
        artifact_type=ArtifactType.RELEASE_NOTE,
        title="Release note",
        uri_or_path="artifacts/release/release-note.md",
        created_by="release-manager",
    )
    assert len(restored.list_artifacts(run.id)) == 2

    metrics = restored.get_metrics()
    assert metrics["total_runs"] == 1
    assert metrics["total_workitems"] == 2
    assert metrics["total_gate_checks"] == 2
    assert metrics["total_artifacts"] == 2
    assert metrics["run_status_counts"]["succeeded"] == 1
