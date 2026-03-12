from __future__ import annotations

from typing import Any

from control_center.models import WorkItem


def normalize_modules(modules: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in modules:
        if not isinstance(item, str):
            raise ValueError("modules must be string values")
        cleaned = item.strip()
        if not cleaned:
            continue
        normalized.append(cleaned)
    unique_modules = list(dict.fromkeys(normalized))
    if not unique_modules:
        raise ValueError("modules must contain at least one non-empty value")
    return unique_modules


def normalize_depends_on_roles(value: Any) -> list[str]:
    if isinstance(value, str):
        tokens = [value]
    elif isinstance(value, list):
        tokens = value
    else:
        return []
    output: list[str] = []
    for item in tokens:
        role = str(item).strip().lower()
        if not role:
            continue
        if role not in output:
            output.append(role)
    return output


def build_default_module_task_package(
    *,
    module: str,
    module_stages: tuple[str, ...],
) -> list[dict[str, str]]:
    return [
        {"role": role, "objective": f"execute {role} stage for module {module}"}
        for role in module_stages
    ]


def build_task_package_item_spec(
    item: dict[str, Any],
) -> tuple[str, list[str], int, dict[str, Any], bool]:
    role = str(item.get("role", "")).strip().lower()
    if not role:
        raise ValueError("module task package role is required")

    objective = str(item.get("objective", "")).strip()
    depends_on_roles = normalize_depends_on_roles(item.get("depends_on_roles"))

    priority = item.get("priority")
    normalized_priority = int(priority) if isinstance(priority, int) else 3
    if normalized_priority < 1 or normalized_priority > 5:
        normalized_priority = 3

    metadata: dict[str, Any] = {"task_source": "chief_decomposition"}
    if objective:
        metadata["task_objective"] = objective

    deliverable = str(item.get("deliverable", "")).strip()
    if deliverable:
        metadata["task_deliverable"] = deliverable
    if depends_on_roles:
        metadata["task_depends_on_roles"] = depends_on_roles

    routing_requires_approval = False
    routing = item.get("routing")
    if isinstance(routing, dict):
        routing_rule_id = str(routing.get("rule_id", "")).strip()
        if routing_rule_id:
            metadata["task_routing_rule_id"] = routing_rule_id
        routing_capability_id = str(routing.get("capability_id", "")).strip()
        if routing_capability_id:
            metadata["task_routing_capability_id"] = routing_capability_id
        routing_executor = str(routing.get("executor", "")).strip()
        if routing_executor:
            metadata["task_routing_executor"] = routing_executor
        required_checks = routing.get("required_checks")
        if isinstance(required_checks, list):
            normalized_checks: list[str] = []
            for check_item in required_checks:
                normalized = str(check_item).strip()
                if not normalized:
                    continue
                if normalized not in normalized_checks:
                    normalized_checks.append(normalized)
            if normalized_checks:
                metadata["task_routing_required_checks"] = normalized_checks
        handoff_roles = routing.get("handoff_roles")
        if isinstance(handoff_roles, list):
            normalized_handoffs: list[str] = []
            for role_item in handoff_roles:
                normalized_role = str(role_item).strip().lower()
                if not normalized_role:
                    continue
                if normalized_role not in normalized_handoffs:
                    normalized_handoffs.append(normalized_role)
            if normalized_handoffs:
                metadata["task_routing_handoff_roles"] = normalized_handoffs
        signals = routing.get("signals")
        if isinstance(signals, dict):
            metadata["task_routing_signals"] = signals
        if bool(routing.get("requires_human_confirmation", False)):
            routing_requires_approval = True
            metadata["task_requires_human_confirmation"] = True

    return role, depends_on_roles, normalized_priority, metadata, routing_requires_approval


def derive_terminal_ids(created: list[WorkItem]) -> list[str]:
    created_ids = [item.id for item in created]
    internal_referenced: set[str] = set()
    created_id_set = set(created_ids)
    for workitem in created:
        for dependency_id in workitem.depends_on:
            if dependency_id in created_id_set:
                internal_referenced.add(dependency_id)
    terminal_ids = [item_id for item_id in created_ids if item_id not in internal_referenced]
    if not terminal_ids and created_ids:
        terminal_ids = [created_ids[-1]]
    return terminal_ids
