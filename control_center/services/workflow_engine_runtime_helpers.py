from __future__ import annotations

from control_center.models import (
    ArtifactType,
    ExecuteWorkflowRunResponse,
    WorkItem,
    WorkItemStatus,
)
from control_center.services.workflow_scheduler import WorkflowScheduler


def build_execution_text(workitem: WorkItem) -> str:
    module_label = workitem.module_key or "unknown-module"
    discussion_resolved = bool(workitem.metadata.get("discussion_resolved"))
    objective = str(workitem.metadata.get("task_objective", "")).strip()
    deliverable = str(workitem.metadata.get("task_deliverable", "")).strip()
    routing_capability_id = str(workitem.metadata.get("task_routing_capability_id", "")).strip()
    routing_rule_id = str(workitem.metadata.get("task_routing_rule_id", "")).strip()
    routing_required_checks = workitem.metadata.get("task_routing_required_checks")
    parts = [
        f"role={workitem.role}",
        f"module={module_label}",
        "execute stage",
        f"discussion_resolved={str(discussion_resolved).lower()}",
    ]
    if objective:
        parts.append(f"objective={objective}")
    if deliverable:
        parts.append(f"deliverable={deliverable}")
    if routing_capability_id:
        parts.append(f"routing_capability={routing_capability_id}")
    if routing_rule_id:
        parts.append(f"routing_rule={routing_rule_id}")
    if isinstance(routing_required_checks, list) and routing_required_checks:
        checks = ",".join(
            str(item).strip() for item in routing_required_checks if str(item).strip()
        )
        if checks:
            parts.append(f"required_checks={checks}")
    return "; ".join(parts)


def find_module_descendants(
    *,
    run_items: list[WorkItem],
    failed_workitem: WorkItem,
) -> list[WorkItem]:
    target_module = failed_workitem.module_key
    pending_like = {
        WorkItemStatus.PENDING,
        WorkItemStatus.READY,
        WorkItemStatus.NEEDS_DISCUSSION,
        WorkItemStatus.RUNNING,
    }
    descendants: list[WorkItem] = []
    frontier = [failed_workitem.id]
    visited: set[str] = set()

    while frontier:
        current = frontier.pop()
        for item in run_items:
            if item.id in visited:
                continue
            if current not in item.depends_on:
                continue
            if item.module_key != target_module:
                continue
            if item.status not in pending_like:
                continue
            visited.add(item.id)
            descendants.append(item)
            frontier.append(item.id)
    return descendants


def rewrite_integration_dependencies(
    depends_on: list[str],
    *,
    old_terminal_id: str,
    new_terminal_id: str,
) -> list[str]:
    return [new_terminal_id if dep == old_terminal_id else dep for dep in depends_on]


def emit_default_artifacts(
    scheduler: WorkflowScheduler,
    workitem: WorkItem,
) -> None:
    role = workitem.role
    if role == "acceptance":
        scheduler.create_artifact(
            workitem.id,
            artifact_type=ArtifactType.ACCEPTANCE_REPORT,
            title=f"Acceptance report for {workitem.module_key or 'global'}",
            uri_or_path=f"artifacts/{workitem.id}/acceptance-report.md",
            created_by=role,
        )
        return
    if role == "release-manager":
        scheduler.create_artifact(
            workitem.id,
            artifact_type=ArtifactType.RELEASE_NOTE,
            title="Release note",
            uri_or_path=f"artifacts/{workitem.id}/release-note.md",
            created_by=role,
        )
        scheduler.create_artifact(
            workitem.id,
            artifact_type=ArtifactType.ROLLBACK_PLAN,
            title="Rollback plan",
            uri_or_path=f"artifacts/{workitem.id}/rollback-plan.md",
            created_by=role,
        )


def build_execute_response(
    *,
    scheduler: WorkflowScheduler,
    run_id: str,
    executed: list[str],
    failed: list[str],
) -> ExecuteWorkflowRunResponse:
    run = scheduler.get_run(run_id)
    all_workitems = scheduler.list_workitems(run_id)
    remaining_ready = [item.id for item in all_workitems if item.status == WorkItemStatus.READY]
    remaining_pending = [
        item.id for item in all_workitems if item.status == WorkItemStatus.PENDING
    ]
    waiting_discussion_ids = scheduler.list_workitem_ids_by_status(
        run_id,
        WorkItemStatus.NEEDS_DISCUSSION,
    )
    waiting_approval_ids = scheduler.list_workitem_ids_by_status(
        run_id,
        WorkItemStatus.WAITING_APPROVAL,
    )
    return ExecuteWorkflowRunResponse(
        run_id=run.id,
        run_status=run.status,
        executed_count=len(executed),
        failed_count=len(failed),
        remaining_ready_count=len(remaining_ready),
        remaining_pending_count=len(remaining_pending),
        waiting_discussion_count=len(waiting_discussion_ids),
        waiting_approval_count=len(waiting_approval_ids),
        executed_workitem_ids=executed,
        failed_workitem_ids=failed,
        waiting_discussion_workitem_ids=waiting_discussion_ids,
        waiting_approval_workitem_ids=waiting_approval_ids,
    )
