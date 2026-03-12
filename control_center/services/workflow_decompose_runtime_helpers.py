from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from control_center.models import ActionExecuteResponse, DecomposeBootstrapWorkflowRequest


@dataclass(slots=True)
class DecomposeResolution:
    modules: list[str]
    required_tags: list[str]
    missing_tags: list[str]
    requirement_module_map: dict[str, list[str]]
    missing_mapping_tags: list[str]
    invalid_mapping_modules: dict[str, list[str]]
    mapping_explicit: bool
    module_task_packages: dict[str, list[dict[str, object]]]
    missing_task_package_modules: list[str]
    invalid_task_package_roles: dict[str, list[str]]
    missing_task_package_roles: dict[str, list[str]]
    task_package_explicit: bool
    chief_metadata: dict[str, object]
    fallback_applied: bool
    fallback_reason: str | None


@dataclass(slots=True)
class PendingDecompositionView:
    confirmation_status: str | None
    confirmation_token: str | None
    requested_by: str | None
    requested_at: str | None
    confirmed_by: str | None
    confirmed_at: str | None
    reason: str | None
    requirements: str | None
    module_hints: list[str]
    max_modules: int | None
    modules: list[str]
    chief_summary: str | None
    chief_agent: str | None
    chief_trace_id: str | None
    chief_metadata: dict[str, object]


def resolve_decomposition_from_chief_result(
    *,
    chief_result: ActionExecuteResponse,
    payload: DecomposeBootstrapWorkflowRequest,
    chief_metadata: dict[str, object],
    decompose_allow_synthetic_fallback: bool,
    decompose_require_explicit_map: bool,
    decompose_require_task_package: bool,
    build_synthetic_decomposition_fallback_handler: Callable[
        [str, list[str], int], dict[str, object] | None
    ],
    extract_modules_from_chief_response_handler: Callable[
        [ActionExecuteResponse, int], list[str]
    ],
    validate_decomposition_coverage_handler: Callable[
        [str, list[str], list[str], dict[str, object]],
        tuple[list[str], list[str]],
    ],
    validate_requirement_module_mapping_handler: Callable[
        [list[str], list[str], dict[str, object]],
        tuple[dict[str, list[str]], list[str], dict[str, list[str]], bool],
    ],
    validate_module_task_packages_handler: Callable[
        [list[str], dict[str, object]],
        tuple[
            dict[str, list[dict[str, object]]],
            list[str],
            dict[str, list[str]],
            dict[str, list[str]],
            bool,
        ],
    ],
) -> DecomposeResolution:
    fallback_applied = False
    fallback_reason: str | None = None

    def _apply_synthetic_fallback(reason_text: str) -> tuple[
        list[str],
        list[str],
        list[str],
        dict[str, list[str]],
        list[str],
        dict[str, list[str]],
        bool,
        dict[str, list[dict[str, object]]],
        list[str],
        dict[str, list[str]],
        dict[str, list[str]],
        bool,
    ]:
        synthetic = build_synthetic_decomposition_fallback_handler(
            payload.requirements,
            payload.module_hints,
            payload.max_modules,
        )
        if synthetic is None:
            raise ValueError(reason_text)

        nonlocal fallback_applied, fallback_reason
        fallback_applied = True
        fallback_reason = reason_text

        fallback_modules = list(synthetic["modules"])
        fallback_required_tags = list(synthetic["required_tags"])
        fallback_missing_tags: list[str] = []
        fallback_requirement_module_map = dict(synthetic["requirement_module_map"])
        fallback_missing_mapping_tags: list[str] = []
        fallback_invalid_mapping_modules: dict[str, list[str]] = {}
        fallback_mapping_explicit = True
        fallback_module_task_packages = dict(synthetic["module_task_packages"])
        fallback_missing_task_package_modules: list[str] = []
        fallback_invalid_task_package_roles: dict[str, list[str]] = {}
        fallback_missing_task_package_roles: dict[str, list[str]] = {}
        fallback_task_package_explicit = True

        decomposition_meta = chief_metadata.get("decomposition")
        if not isinstance(decomposition_meta, dict):
            decomposition_meta = {}
        decomposition_meta["requirement_module_map"] = fallback_requirement_module_map
        decomposition_meta["module_task_packages"] = fallback_module_task_packages
        decomposition_meta["coverage_tags"] = fallback_required_tags
        decomposition_meta["synthetic_fallback"] = True
        decomposition_meta["synthetic_fallback_reason"] = fallback_reason
        chief_metadata["decomposition"] = decomposition_meta
        chief_metadata["requirement_module_map"] = fallback_requirement_module_map
        chief_metadata["module_task_packages"] = fallback_module_task_packages
        chief_metadata["coverage_tags"] = fallback_required_tags
        chief_metadata["modules"] = fallback_modules
        chief_metadata["synthetic_fallback"] = True
        chief_metadata["synthetic_fallback_reason"] = fallback_reason

        return (
            fallback_modules,
            fallback_required_tags,
            fallback_missing_tags,
            fallback_requirement_module_map,
            fallback_missing_mapping_tags,
            fallback_invalid_mapping_modules,
            fallback_mapping_explicit,
            fallback_module_task_packages,
            fallback_missing_task_package_modules,
            fallback_invalid_task_package_roles,
            fallback_missing_task_package_roles,
            fallback_task_package_explicit,
        )

    if chief_result.status != "success":
        if not decompose_allow_synthetic_fallback:
            raise ValueError(f"chief decomposition failed: status={chief_result.status}")
        (
            modules,
            required_tags,
            missing_tags,
            requirement_module_map,
            missing_mapping_tags,
            invalid_mapping_modules,
            mapping_explicit,
            module_task_packages,
            missing_task_package_modules,
            invalid_task_package_roles,
            missing_task_package_roles,
            task_package_explicit,
        ) = _apply_synthetic_fallback(f"chief status={chief_result.status}")
    else:
        modules = extract_modules_from_chief_response_handler(
            chief_result,
            payload.max_modules,
        )
        if not modules:
            if not decompose_allow_synthetic_fallback:
                raise ValueError("chief decomposition returned no modules")
            (
                modules,
                required_tags,
                missing_tags,
                requirement_module_map,
                missing_mapping_tags,
                invalid_mapping_modules,
                mapping_explicit,
                module_task_packages,
                missing_task_package_modules,
                invalid_task_package_roles,
                missing_task_package_roles,
                task_package_explicit,
            ) = _apply_synthetic_fallback("chief decomposition returned no modules")
        else:
            required_tags, missing_tags = validate_decomposition_coverage_handler(
                payload.requirements,
                payload.module_hints,
                modules,
                chief_metadata,
            )
            if missing_tags:
                raise ValueError(
                    "chief decomposition missing required coverage tags: "
                    + ", ".join(missing_tags)
                )

            (
                requirement_module_map,
                missing_mapping_tags,
                invalid_mapping_modules,
                mapping_explicit,
            ) = validate_requirement_module_mapping_handler(
                required_tags,
                modules,
                chief_metadata,
            )
            if required_tags and decompose_require_explicit_map and not mapping_explicit:
                raise ValueError("chief decomposition missing requirement-module mapping")
            if invalid_mapping_modules:
                invalid_refs = ", ".join(
                    f"{tag}=>{','.join(values)}"
                    for tag, values in sorted(invalid_mapping_modules.items())
                )
                raise ValueError(
                    "chief decomposition requirement-module mapping references unknown modules: "
                    + invalid_refs
                )
            if missing_mapping_tags:
                raise ValueError(
                    "chief decomposition missing requirement-module mappings for tags: "
                    + ", ".join(missing_mapping_tags)
                )

            (
                module_task_packages,
                missing_task_package_modules,
                invalid_task_package_roles,
                missing_task_package_roles,
                task_package_explicit,
            ) = validate_module_task_packages_handler(
                modules,
                chief_metadata,
            )
            if modules and decompose_require_task_package and not task_package_explicit:
                raise ValueError("chief decomposition missing module task packages")
            if missing_task_package_modules:
                raise ValueError(
                    "chief decomposition module task packages missing modules: "
                    + ", ".join(missing_task_package_modules)
                )
            if invalid_task_package_roles:
                invalid_role_text = ", ".join(
                    f"{module}=>{','.join(roles)}"
                    for module, roles in sorted(invalid_task_package_roles.items())
                )
                raise ValueError(
                    "chief decomposition module task packages contain invalid roles: "
                    + invalid_role_text
                )
            if missing_task_package_roles:
                missing_role_text = ", ".join(
                    f"{module}=>{','.join(roles)}"
                    for module, roles in sorted(missing_task_package_roles.items())
                )
                raise ValueError(
                    "chief decomposition module task packages missing required roles: "
                    + missing_role_text
                )

    return DecomposeResolution(
        modules=modules,
        required_tags=required_tags,
        missing_tags=missing_tags,
        requirement_module_map=requirement_module_map,
        missing_mapping_tags=missing_mapping_tags,
        invalid_mapping_modules=invalid_mapping_modules,
        mapping_explicit=mapping_explicit,
        module_task_packages=module_task_packages,
        missing_task_package_modules=missing_task_package_modules,
        invalid_task_package_roles=invalid_task_package_roles,
        missing_task_package_roles=missing_task_package_roles,
        task_package_explicit=task_package_explicit,
        chief_metadata=chief_metadata,
        fallback_applied=fallback_applied,
        fallback_reason=fallback_reason,
    )


def build_pending_decomposition_view(
    pending: dict[str, object],
    *,
    optional_text_handler: Callable[[object], str | None],
    normalize_module_candidates_handler: Callable[[list[object]], list[str]],
) -> PendingDecompositionView:
    confirmation = pending.get("confirmation")
    confirmation_payload = confirmation if isinstance(confirmation, dict) else {}
    confirmation_status = optional_text_handler(confirmation_payload.get("status"))

    pending_modules = pending.get("modules")
    modules = (
        normalize_module_candidates_handler(pending_modules)
        if isinstance(pending_modules, list)
        else []
    )

    raw_module_hints = pending.get("module_hints")
    module_hints: list[str] = []
    if isinstance(raw_module_hints, list):
        for hint in raw_module_hints:
            normalized_hint = optional_text_handler(hint)
            if normalized_hint:
                module_hints.append(normalized_hint)

    raw_chief_metadata = pending.get("chief_metadata")
    chief_metadata = raw_chief_metadata if isinstance(raw_chief_metadata, dict) else {}

    max_modules_value = pending.get("max_modules")
    max_modules = max_modules_value if isinstance(max_modules_value, int) else None

    return PendingDecompositionView(
        confirmation_status=confirmation_status,
        confirmation_token=optional_text_handler(confirmation_payload.get("token")),
        requested_by=optional_text_handler(confirmation_payload.get("requested_by")),
        requested_at=optional_text_handler(confirmation_payload.get("requested_at")),
        confirmed_by=optional_text_handler(confirmation_payload.get("confirmed_by")),
        confirmed_at=optional_text_handler(confirmation_payload.get("confirmed_at")),
        reason=optional_text_handler(confirmation_payload.get("reason")),
        requirements=optional_text_handler(pending.get("requirements")),
        module_hints=module_hints,
        max_modules=max_modules,
        modules=modules,
        chief_summary=optional_text_handler(pending.get("chief_summary")),
        chief_agent=optional_text_handler(pending.get("chief_agent")),
        chief_trace_id=optional_text_handler(pending.get("chief_trace_id")),
        chief_metadata=chief_metadata,
    )


def extract_pending_confirmation_state(
    pending: dict[str, object],
) -> tuple[dict[str, object], str, str]:
    confirmation = pending.get("confirmation")
    if not isinstance(confirmation, dict):
        raise ValueError("pending decomposition has no confirmation state")

    current_status = str(confirmation.get("status", "")).strip().lower()
    token = str(confirmation.get("token", "")).strip()
    return confirmation, current_status, token


def extract_pending_modules(
    pending: dict[str, object],
    *,
    normalize_module_candidates_handler: Callable[[list[object]], list[str]],
) -> list[str]:
    pending_modules = pending.get("modules")
    if not isinstance(pending_modules, list):
        raise ValueError("pending decomposition has no modules")
    modules = normalize_module_candidates_handler(pending_modules)
    if not modules:
        raise ValueError("pending decomposition has no valid modules")
    return modules


def normalize_pending_module_task_packages(
    pending_task_packages: object,
) -> dict[str, list[dict[str, object]]] | None:
    if not isinstance(pending_task_packages, dict):
        return None
    normalized_packages: dict[str, list[dict[str, object]]] = {}
    for module_key, tasks in pending_task_packages.items():
        if not isinstance(module_key, str):
            continue
        if not isinstance(tasks, list):
            continue
        normalized_rows = [item for item in tasks if isinstance(item, dict)]
        if normalized_rows:
            normalized_packages[module_key] = normalized_rows
    if normalized_packages:
        return normalized_packages
    return None
