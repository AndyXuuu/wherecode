import asyncio

from control_center.models import ActionExecuteResponse, DiscussionPrompt
from control_center.services import WorkflowEngine, WorkflowScheduler


async def _ok_executor(request) -> ActionExecuteResponse:
    return ActionExecuteResponse(
        status="success",
        summary=f"ok:{request.role}:{request.module_key}",
        agent=request.agent or "coding-agent",
        trace_id="act_engine_ok",
    )


async def _mixed_executor(request) -> ActionExecuteResponse:
    text = request.text.lower()
    if "billing" in text:
        return ActionExecuteResponse(
            status="failed",
            summary="billing failed",
            agent=request.agent or "coding-agent",
            trace_id="act_engine_fail",
        )
    return ActionExecuteResponse(
        status="success",
        summary="ok",
        agent=request.agent or "coding-agent",
        trace_id="act_engine_ok",
    )


async def _discussion_executor(request) -> ActionExecuteResponse:
    text = request.text.lower()
    if "role=module-dev" in text and "module=needs-discussion" in text:
        if "discussion_resolved=true" not in text:
            return ActionExecuteResponse(
                status="needs_discussion",
                summary="need discussion",
                agent=request.agent or "coding-agent",
                trace_id="act_engine_discuss",
                discussion=DiscussionPrompt(
                    question="choose strategy",
                    options=["a", "b"],
                    recommendation="a",
                    fingerprint="fp-engine-discuss",
                ),
            )
    return ActionExecuteResponse(
        status="success",
        summary="ok",
        agent=request.agent or "coding-agent",
        trace_id="act_engine_ok",
    )


def test_bootstrap_creates_expected_workitems() -> None:
    scheduler = WorkflowScheduler()
    engine = WorkflowEngine(scheduler=scheduler, action_executor=_ok_executor)
    run = scheduler.create_run(project_id="proj_alpha")

    result = engine.bootstrap_standard_pipeline(run.id, ["auth", "billing"])

    assert len(result.workitems) == 11
    roles = [item.role for item in result.workitems]
    assert roles.count("module-dev") == 2
    assert roles[-3:] == ["integration-test", "acceptance", "release-manager"]


def test_execute_until_blocked_succeeds_for_all_workitems() -> None:
    scheduler = WorkflowScheduler()
    engine = WorkflowEngine(scheduler=scheduler, action_executor=_ok_executor)
    run = scheduler.create_run(project_id="proj_alpha")
    engine.bootstrap_standard_pipeline(run.id, ["auth"])

    response = asyncio.run(engine.execute_until_blocked(run.id, max_loops=20))
    assert response.run_status == "succeeded"
    assert response.failed_count == 0
    assert response.remaining_pending_count == 0


def test_execute_until_blocked_marks_failed_when_stage_fails() -> None:
    scheduler = WorkflowScheduler()
    engine = WorkflowEngine(scheduler=scheduler, action_executor=_mixed_executor)
    run = scheduler.create_run(project_id="proj_alpha")
    engine.bootstrap_standard_pipeline(run.id, ["auth", "billing"])

    response = asyncio.run(engine.execute_until_blocked(run.id, max_loops=20))
    assert response.run_status == "failed"
    assert response.failed_count >= 1


def test_execute_until_blocked_handles_discussion_and_resume() -> None:
    scheduler = WorkflowScheduler()
    engine = WorkflowEngine(scheduler=scheduler, action_executor=_discussion_executor)
    run = scheduler.create_run(project_id="proj_alpha")
    engine.bootstrap_standard_pipeline(run.id, ["needs-discussion"])

    first = asyncio.run(engine.execute_until_blocked(run.id, max_loops=20))
    assert first.run_status == "blocked"
    assert first.waiting_discussion_count >= 1

    target = next(
        item
        for item in scheduler.list_workitems(run.id)
        if item.role == "module-dev" and item.module_key == "needs-discussion"
    )
    scheduler.resolve_discussion(
        target.id,
        decision="go with option a",
        resolved_by_role="chief-architect",
    )

    second = asyncio.run(engine.execute_until_blocked(run.id, max_loops=20))
    assert second.run_status == "succeeded"
    assert second.failed_count == 0


def test_gate_fail_once_triggers_reflow_and_eventual_success() -> None:
    scheduler = WorkflowScheduler()
    engine = WorkflowEngine(scheduler=scheduler, action_executor=_ok_executor, max_module_reflows=1)
    run = scheduler.create_run(project_id="proj_alpha")
    engine.bootstrap_standard_pipeline(run.id, ["doc-reflow-once"])

    response = asyncio.run(engine.execute_until_blocked(run.id, max_loops=50))
    assert response.run_status == "succeeded"
    gates = scheduler.list_gate_checks(run.id)
    assert any(gate.status == "failed" for gate in gates)
    assert any(gate.status == "passed" for gate in gates)


def test_gate_fail_persistent_reflow_exhaustion_fails_run() -> None:
    scheduler = WorkflowScheduler()
    engine = WorkflowEngine(scheduler=scheduler, action_executor=_ok_executor, max_module_reflows=1)
    run = scheduler.create_run(project_id="proj_alpha")
    engine.bootstrap_standard_pipeline(run.id, ["doc-fail"])

    response = asyncio.run(engine.execute_until_blocked(run.id, max_loops=50))
    assert response.run_status == "failed"
    assert response.failed_count >= 1


def test_release_requires_approval_blocks_then_resumes() -> None:
    scheduler = WorkflowScheduler()
    engine = WorkflowEngine(
        scheduler=scheduler,
        action_executor=_ok_executor,
        release_requires_approval=True,
    )
    run = scheduler.create_run(project_id="proj_alpha")
    engine.bootstrap_standard_pipeline(run.id, ["auth"])

    first = asyncio.run(engine.execute_until_blocked(run.id, max_loops=50))
    assert first.run_status == "waiting_approval"
    assert first.waiting_approval_count == 1
    assert len(first.waiting_approval_workitem_ids) == 1

    scheduler.approve_workitem(first.waiting_approval_workitem_ids[0], approved_by="owner")
    second = asyncio.run(engine.execute_until_blocked(run.id, max_loops=50))
    assert second.run_status == "succeeded"

    artifacts = scheduler.list_artifacts(run.id)
    artifact_types = {item.artifact_type for item in artifacts}
    assert "acceptance_report" in artifact_types
    assert "release_note" in artifact_types
    assert "rollback_plan" in artifact_types
