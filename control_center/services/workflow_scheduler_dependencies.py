from __future__ import annotations

from control_center.models import WorkItem, WorkItemStatus


def validate_dependency_ids(
    run_id: str,
    dependency_ids: list[str],
    workitems: dict[str, WorkItem],
    workitem_run: dict[str, str],
) -> None:
    for dependency_id in dependency_ids:
        if dependency_id not in workitems:
            raise ValueError(f"dependency workitem not found: {dependency_id}")
        dependency_run_id = workitem_run.get(dependency_id)
        if dependency_run_id != run_id:
            raise ValueError(f"dependency workitem {dependency_id} is in another workflow run")


def dependencies_satisfied(
    item: WorkItem,
    workitems: dict[str, WorkItem],
) -> bool:
    if not item.depends_on:
        return True
    for dependency_id in item.depends_on:
        dependency = workitems.get(dependency_id)
        if dependency is None:
            return False
        if dependency.status not in {WorkItemStatus.SUCCEEDED, WorkItemStatus.SKIPPED}:
            return False
    return True


def select_pending_ready_for_transition(
    *,
    run_workitem_ids: list[str],
    workitems: dict[str, WorkItem],
) -> list[WorkItem]:
    selected: list[WorkItem] = []
    for item_id in run_workitem_ids:
        item = workitems[item_id]
        if item.status != WorkItemStatus.PENDING:
            continue
        if dependencies_satisfied(item, workitems):
            selected.append(item)
    return selected


def normalize_dependency_update_ids(
    *,
    workitem_id: str,
    dependency_ids: list[str],
) -> list[str]:
    normalized = [value.strip() for value in dependency_ids if value.strip()]
    if workitem_id in normalized:
        raise ValueError("workitem cannot depend on itself")
    if len(set(normalized)) != len(normalized):
        raise ValueError("dependency ids must not contain duplicates")
    return normalized
