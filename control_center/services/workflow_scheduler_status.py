from __future__ import annotations

from control_center.models import (
    Artifact,
    GateCheck,
    WorkItem,
    WorkItemStatus,
    WorkflowRun,
    WorkflowRunStatus,
)


def derive_run_status(items: list[WorkItem]) -> WorkflowRunStatus:
    if not items:
        return WorkflowRunStatus.PLANNING

    statuses = {item.status for item in items}
    if WorkItemStatus.FAILED in statuses:
        return WorkflowRunStatus.FAILED
    if WorkItemStatus.NEEDS_DISCUSSION in statuses:
        return WorkflowRunStatus.BLOCKED
    if WorkItemStatus.WAITING_APPROVAL in statuses:
        return WorkflowRunStatus.WAITING_APPROVAL
    if statuses.issubset({WorkItemStatus.SUCCEEDED, WorkItemStatus.SKIPPED}):
        return WorkflowRunStatus.SUCCEEDED
    return WorkflowRunStatus.RUNNING


def build_scheduler_metrics(
    *,
    runs: dict[str, WorkflowRun],
    workitems: dict[str, WorkItem],
    gate_checks: dict[str, GateCheck],
    artifacts: dict[str, Artifact],
) -> dict[str, object]:
    run_status_counts: dict[str, int] = {}
    for run in runs.values():
        key = run.status.value
        run_status_counts[key] = run_status_counts.get(key, 0) + 1

    workitem_status_counts: dict[str, int] = {}
    for item in workitems.values():
        key = item.status.value
        workitem_status_counts[key] = workitem_status_counts.get(key, 0) + 1

    gate_status_counts: dict[str, int] = {}
    for gate in gate_checks.values():
        key = gate.status.value
        gate_status_counts[key] = gate_status_counts.get(key, 0) + 1

    artifact_type_counts: dict[str, int] = {}
    for artifact in artifacts.values():
        key = artifact.artifact_type.value
        artifact_type_counts[key] = artifact_type_counts.get(key, 0) + 1

    return {
        "total_runs": len(runs),
        "run_status_counts": run_status_counts,
        "total_workitems": len(workitems),
        "workitem_status_counts": workitem_status_counts,
        "total_gate_checks": len(gate_checks),
        "gate_status_counts": gate_status_counts,
        "total_artifacts": len(artifacts),
        "artifact_type_counts": artifact_type_counts,
    }
