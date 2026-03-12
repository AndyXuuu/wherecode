from __future__ import annotations

from control_center.services.dev_routing_matrix import normalize_task_routing


def required_module_roles() -> tuple[str, ...]:
    return ("module-dev", "doc-manager", "qa-test", "security-review")


def _normalize_task_items(value: object) -> list[dict[str, object]]:
    normalized_items: list[dict[str, object]] = []
    if not isinstance(value, list):
        return normalized_items
    for item in value:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        objective = str(
            item.get("objective")
            or item.get("goal")
            or item.get("task")
            or ""
        ).strip()
        if not role or not objective:
            continue
        deliverable = str(item.get("deliverable", "")).strip()
        row: dict[str, object] = {"role": role, "objective": objective}
        if deliverable:
            row["deliverable"] = deliverable
        raw_depends_on_roles = item.get("depends_on_roles")
        if raw_depends_on_roles is None:
            raw_depends_on_roles = item.get("depends_on")
        depends_on_roles: list[str] = []
        if isinstance(raw_depends_on_roles, str):
            normalized_dep = raw_depends_on_roles.strip().lower()
            if normalized_dep:
                depends_on_roles.append(normalized_dep)
        elif isinstance(raw_depends_on_roles, list):
            for dep_item in raw_depends_on_roles:
                normalized_dep = str(dep_item).strip().lower()
                if not normalized_dep:
                    continue
                if normalized_dep not in depends_on_roles:
                    depends_on_roles.append(normalized_dep)
        if depends_on_roles:
            row["depends_on_roles"] = depends_on_roles
        raw_priority = item.get("priority")
        if isinstance(raw_priority, int) and 1 <= raw_priority <= 5:
            row["priority"] = raw_priority
        routing = normalize_task_routing(item.get("routing"))
        if routing:
            row["routing"] = routing
        normalized_items.append(row)
    return normalized_items


def extract_module_task_packages(
    chief_metadata: dict[str, object],
) -> tuple[dict[str, list[dict[str, object]]], bool]:
    if not isinstance(chief_metadata, dict):
        return {}, False

    packages: dict[str, list[dict[str, object]]] = {}
    explicit = False

    def _upsert(module_key: object, tasks: object) -> None:
        module = str(module_key).strip()
        if not module:
            return
        normalized_tasks = _normalize_task_items(tasks)
        if not normalized_tasks:
            return
        existing = packages.get(module, [])
        for task in normalized_tasks:
            if task not in existing:
                existing.append(task)
        packages[module] = existing

    direct = chief_metadata.get("module_task_packages")
    if isinstance(direct, dict):
        explicit = True
        for module_key, tasks in direct.items():
            _upsert(module_key, tasks)

    decomposition = chief_metadata.get("decomposition")
    if isinstance(decomposition, dict):
        nested = decomposition.get("module_task_packages")
        if isinstance(nested, dict):
            explicit = True
            for module_key, tasks in nested.items():
                _upsert(module_key, tasks)

        module_items = decomposition.get("modules")
        if isinstance(module_items, list):
            for item in module_items:
                if not isinstance(item, dict):
                    continue
                module_key = item.get("module_key")
                task_package = item.get("task_package")
                if isinstance(module_key, str):
                    normalized_tasks = _normalize_task_items(task_package)
                    if normalized_tasks:
                        explicit = True
                        _upsert(module_key, normalized_tasks)

    return packages, explicit


def infer_default_task_packages(
    modules: list[str],
) -> dict[str, list[dict[str, str]]]:
    output: dict[str, list[dict[str, str]]] = {}
    for module in modules:
        tasks: list[dict[str, str]] = []
        for role in required_module_roles():
            tasks.append(
                {
                    "role": role,
                    "objective": f"execute {role} stage for module {module}",
                }
            )
        output[module] = tasks
    return output


def validate_module_task_packages(
    modules: list[str],
    chief_metadata: dict[str, object],
) -> tuple[
    dict[str, list[dict[str, object]]],
    list[str],
    dict[str, list[str]],
    dict[str, list[str]],
    bool,
]:
    packages, explicit = extract_module_task_packages(chief_metadata)
    if not packages:
        packages = infer_default_task_packages(modules)

    module_set = {item.strip() for item in modules if item.strip()}
    required_roles = set(required_module_roles())

    normalized_packages: dict[str, list[dict[str, object]]] = {}
    missing_modules: list[str] = []
    invalid_roles: dict[str, list[str]] = {}
    missing_roles: dict[str, list[str]] = {}

    for module in modules:
        module_tasks = packages.get(module, [])
        if not module_tasks:
            missing_modules.append(module)
            continue

        role_seen: set[str] = set()
        normalized_tasks: list[dict[str, object]] = []
        current_invalid_roles: list[str] = []
        for task in module_tasks:
            role = str(task.get("role", "")).strip().lower()
            objective = str(task.get("objective", "")).strip()
            if not role or not objective:
                continue
            if role not in required_roles:
                if role not in current_invalid_roles:
                    current_invalid_roles.append(role)
                continue
            role_seen.add(role)
            row: dict[str, object] = {"role": role, "objective": objective}
            deliverable = str(task.get("deliverable", "")).strip()
            if deliverable:
                row["deliverable"] = deliverable
            raw_depends_on_roles = task.get("depends_on_roles")
            depends_on_roles: list[str] = []
            if isinstance(raw_depends_on_roles, list):
                for dep_item in raw_depends_on_roles:
                    normalized_dep = str(dep_item).strip().lower()
                    if not normalized_dep:
                        continue
                    if normalized_dep not in required_roles:
                        continue
                    if normalized_dep not in depends_on_roles:
                        depends_on_roles.append(normalized_dep)
            if depends_on_roles:
                row["depends_on_roles"] = depends_on_roles
            raw_priority = task.get("priority")
            if isinstance(raw_priority, int) and 1 <= raw_priority <= 5:
                row["priority"] = raw_priority
            routing = normalize_task_routing(task.get("routing"))
            if routing:
                row["routing"] = routing
            if row not in normalized_tasks:
                normalized_tasks.append(row)

        if current_invalid_roles:
            invalid_roles[module] = current_invalid_roles

        missing_current_roles = sorted(required_roles - role_seen)
        if missing_current_roles:
            missing_roles[module] = missing_current_roles

        if normalized_tasks:
            normalized_packages[module] = normalized_tasks
        else:
            missing_modules.append(module)

    unknown_modules = sorted(set(packages.keys()) - module_set)
    for module in unknown_modules:
        invalid_roles[module] = invalid_roles.get(module, [])
        if "__unknown_module__" not in invalid_roles[module]:
            invalid_roles[module].append("__unknown_module__")

    return normalized_packages, missing_modules, invalid_roles, missing_roles, explicit
