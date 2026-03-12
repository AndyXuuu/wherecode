from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from control_center.models import (
    DecomposeBootstrapAggregateStatusResponse,
    ExecuteWorkflowRunResponse,
    WorkflowRun,
    WorkflowRunOrchestrateDecompositionSummary,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateTelemetryRecord,
    WorkflowRunOrchestrateTelemetrySnapshot,
)


def build_orchestrate_decomposition_summary_impl(
    *,
    run: WorkflowRun,
    aggregate_status: DecomposeBootstrapAggregateStatusResponse,
    select_decomposition_for_preview_handler: Callable[
        [WorkflowRun], tuple[dict[str, object] | None, str]
    ],
    extract_preview_modules_handler: Callable[[dict[str, object]], list[str]],
    get_pending_decomposition_handler: Callable[[WorkflowRun], dict[str, object] | None],
    optional_text_handler: Callable[[object], str | None],
) -> WorkflowRunOrchestrateDecompositionSummary | None:
    decomposition, source = select_decomposition_for_preview_handler(run)
    if decomposition is None:
        return None

    modules = extract_preview_modules_handler(decomposition)
    required_coverage_tags_raw = decomposition.get("required_coverage_tags")
    required_coverage_tags: list[str] = []
    if isinstance(required_coverage_tags_raw, list):
        for item in required_coverage_tags_raw:
            tag = optional_text_handler(item)
            if tag and tag not in required_coverage_tags:
                required_coverage_tags.append(tag)

    requirement_module_map = decomposition.get("requirement_module_map")
    mapped_requirement_tag_count = (
        len(requirement_module_map) if isinstance(requirement_module_map, dict) else 0
    )

    chief_metadata = decomposition.get("chief_metadata")
    requirement_points_count = 0
    if isinstance(chief_metadata, dict):
        nested_decomposition = chief_metadata.get("decomposition")
        if isinstance(nested_decomposition, dict):
            requirement_points = nested_decomposition.get("requirement_points")
            if isinstance(requirement_points, list):
                requirement_points_count = len(
                    [item for item in requirement_points if optional_text_handler(item)]
                )

    role_counts: dict[str, int] = {}
    module_task_count = 0
    module_task_packages = decomposition.get("module_task_packages")
    if isinstance(module_task_packages, dict):
        for tasks in module_task_packages.values():
            if not isinstance(tasks, list):
                continue
            for item in tasks:
                if not isinstance(item, dict):
                    continue
                module_task_count += 1
                role = optional_text_handler(item.get("role"))
                if role:
                    normalized_role = role.lower()
                    role_counts[normalized_role] = (
                        role_counts.get(normalized_role, 0) + 1
                    )

    confirmation_status = None
    pending = get_pending_decomposition_handler(run)
    if pending is not None:
        confirmation = pending.get("confirmation")
        if isinstance(confirmation, dict):
            confirmation_status = optional_text_handler(confirmation.get("status"))
    if confirmation_status is None:
        chief = run.metadata.get("chief_decomposition")
        if isinstance(chief, dict):
            confirmation = chief.get("confirmation")
            if isinstance(confirmation, dict):
                confirmation_status = optional_text_handler(confirmation.get("status"))

    return WorkflowRunOrchestrateDecompositionSummary(
        source=source,
        modules=modules,
        module_count=len(modules),
        module_task_count=module_task_count,
        module_task_role_counts={key: role_counts[key] for key in sorted(role_counts.keys())},
        required_coverage_tags=required_coverage_tags,
        mapped_requirement_tag_count=mapped_requirement_tag_count,
        requirement_points_count=requirement_points_count,
        confirmation_status=confirmation_status,
        has_pending_confirmation=aggregate_status.has_pending_confirmation,
        preview_ready=aggregate_status.preview_ready,
        preview_stale=aggregate_status.preview_stale,
        preview_generated_at=aggregate_status.preview_generated_at,
        workitem_total=aggregate_status.workitem_total,
        next_action=aggregate_status.next_action,
    )


def count_unfinished_workitems_from_aggregate_status(
    status: DecomposeBootstrapAggregateStatusResponse,
) -> int:
    counts = status.workitem_status_counts
    return (
        counts.get("pending", 0)
        + counts.get("ready", 0)
        + counts.get("running", 0)
        + counts.get("waiting_approval", 0)
        + counts.get("needs_discussion", 0)
    )


def build_orchestrate_telemetry_snapshot_impl(
    *,
    started_at: datetime,
    finished_at: datetime,
    actions: list[str],
    status_before: DecomposeBootstrapAggregateStatusResponse,
    status_after: DecomposeBootstrapAggregateStatusResponse,
    execute_result: ExecuteWorkflowRunResponse | None,
) -> WorkflowRunOrchestrateTelemetrySnapshot:
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    if duration_ms < 0:
        duration_ms = 0

    unfinished_before = count_unfinished_workitems_from_aggregate_status(status_before)
    unfinished_after = count_unfinished_workitems_from_aggregate_status(status_after)

    execute_run_status: str | None = None
    execute_failed_count: int | None = None
    execute_remaining_pending_count: int | None = None
    if execute_result is not None:
        execute_run_status = execute_result.run_status
        execute_failed_count = execute_result.failed_count
        execute_remaining_pending_count = execute_result.remaining_pending_count

    return WorkflowRunOrchestrateTelemetrySnapshot(
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        action_count=len(actions),
        actions=actions,
        workitem_total_before=status_before.workitem_total,
        workitem_total_after=status_after.workitem_total,
        workitem_total_delta=(status_after.workitem_total - status_before.workitem_total),
        unfinished_workitem_before=unfinished_before,
        unfinished_workitem_after=unfinished_after,
        unfinished_workitem_delta=(unfinished_after - unfinished_before),
        pending_confirmation_before=status_before.has_pending_confirmation,
        pending_confirmation_after=status_after.has_pending_confirmation,
        pending_confirmation_cleared=(
            status_before.has_pending_confirmation and not status_after.has_pending_confirmation
        ),
        preview_ready_before=status_before.preview_ready,
        preview_ready_after=status_after.preview_ready,
        preview_state_changed=(
            status_before.preview_ready != status_after.preview_ready
            or status_before.preview_stale != status_after.preview_stale
        ),
        next_action_before=status_before.next_action,
        next_action_after=status_after.next_action,
        next_action_changed=(status_before.next_action != status_after.next_action),
        decompose_triggered=("decompose_bootstrap" in actions),
        execute_triggered=("execute_workflow_run" in actions),
        execute_run_status=execute_run_status,
        execute_failed_count=execute_failed_count,
        execute_remaining_pending_count=execute_remaining_pending_count,
    )


def resolve_orchestrate_recovery_action_impl(
    *,
    payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
    latest_record: WorkflowRunOrchestrateTelemetryRecord | None,
    optional_text_handler: Callable[[object], str | None],
) -> tuple[str | None, str]:
    explicit_action = optional_text_handler(payload.action)
    if explicit_action:
        return explicit_action.lower(), "request"
    if (
        latest_record is not None
        and latest_record.decision_report is not None
        and latest_record.decision_report.machine.primary_recovery_action
    ):
        return (
            latest_record.decision_report.machine.primary_recovery_action,
            "latest_primary",
        )
    return None, "none"
