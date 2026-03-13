from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class ControlCenterBootstrapConfig:
    log_level: str
    action_layer_timeout_seconds: float
    action_layer_base_url: str
    agent_routing_file: str
    auth_enabled: bool
    auth_token: str
    decompose_require_explicit_map: bool
    decompose_require_task_package: bool
    decompose_require_confirmation: bool
    decompose_allow_synthetic_fallback: bool
    metrics_alert_policy_update_roles: set[str]
    metrics_rollback_requires_approval: bool
    metrics_rollback_approval_ttl_seconds: int
    metrics_rollback_approver_roles: set[str]
    command_orchestrate_policy_enabled: bool
    command_orchestrate_prefixes: tuple[str, ...]
    command_orchestrate_default_max_modules: int
    command_orchestrate_default_strategy: str
    command_orchestrate_restart_canceled_policy: str
    dev_routing_matrix_file: str
    agent_rules_registry_file: str
    state_backend: str
    sqlite_path: str
    max_module_reflows: int
    release_approval_required: bool
    role_routing_policy_file: str
    metrics_alert_policy_file: str
    metrics_alert_audit_file: str
    metrics_rollback_approval_file: str
    metrics_rollback_approval_purge_audit_file: str
    allowed_origins_raw: str


def _parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _parse_float(value: str, *, default: float) -> float:
    try:
        return float(value.strip())
    except ValueError:
        return default


def _parse_int(value: str, *, default: int) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return default


def _parse_roles_csv(value: str) -> set[str]:
    return {
        role.strip().lower()
        for role in value.split(",")
        if role.strip()
    }


def _parse_prefixes_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _clamp(value: int, *, minimum: int, maximum: int) -> int:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _normalize_restart_canceled_policy(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized in {"always", "on"}:
        return "always"
    if normalized in {"auto", "auto_if_no_requirements"}:
        return "auto_if_no_requirements"
    return "off"


def load_control_center_bootstrap_config(
    env_get: Callable[[str, str], str] = os.getenv,
) -> ControlCenterBootstrapConfig:
    command_orchestrate_default_max_modules = _clamp(
        _parse_int(
            env_get("WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES", "6"),
            default=6,
        ),
        minimum=1,
        maximum=20,
    )
    return ControlCenterBootstrapConfig(
        log_level=env_get("WHERECODE_LOG_LEVEL", "INFO"),
        action_layer_timeout_seconds=_parse_float(
            env_get("ACTION_LAYER_TIMEOUT_SECONDS", "180"),
            default=180.0,
        ),
        action_layer_base_url=env_get(
            "ACTION_LAYER_BASE_URL",
            "http://127.0.0.1:8100",
        ),
        agent_routing_file=env_get(
            "WHERECODE_AGENT_ROUTING_FILE",
            "control_center/agents.routing.json",
        ),
        auth_enabled=_parse_bool(env_get("WHERECODE_AUTH_ENABLED", "true")),
        auth_token=env_get("WHERECODE_TOKEN", "change-me"),
        decompose_require_explicit_map=_parse_bool(
            env_get("WHERECODE_DECOMPOSE_REQUIRE_EXPLICIT_MAP", "true")
        ),
        decompose_require_task_package=_parse_bool(
            env_get("WHERECODE_DECOMPOSE_REQUIRE_TASK_PACKAGE", "true")
        ),
        decompose_require_confirmation=_parse_bool(
            env_get("WHERECODE_DECOMPOSE_REQUIRE_CONFIRMATION", "true")
        ),
        decompose_allow_synthetic_fallback=_parse_bool(
            env_get("WHERECODE_DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK", "true")
        ),
        metrics_alert_policy_update_roles=_parse_roles_csv(
            env_get(
                "WHERECODE_METRICS_ALERT_POLICY_UPDATE_ROLES",
                "ops-admin,chief-architect,release-manager",
            )
        ),
        metrics_rollback_requires_approval=_parse_bool(
            env_get("WHERECODE_METRICS_ROLLBACK_REQUIRES_APPROVAL", "false")
        ),
        metrics_rollback_approval_ttl_seconds=_parse_int(
            env_get("WHERECODE_METRICS_ROLLBACK_APPROVAL_TTL_SECONDS", "86400"),
            default=86400,
        ),
        metrics_rollback_approver_roles=_parse_roles_csv(
            env_get(
                "WHERECODE_METRICS_ROLLBACK_APPROVER_ROLES",
                "ops-admin,release-manager,chief-architect",
            )
        ),
        command_orchestrate_policy_enabled=_parse_bool(
            env_get("WHERECODE_COMMAND_ORCHESTRATE_POLICY_ENABLED", "true")
        ),
        command_orchestrate_prefixes=_parse_prefixes_csv(
            env_get(
                "WHERECODE_COMMAND_ORCHESTRATE_PREFIXES",
                "/orchestrate,orchestrate:,编排:,主流程:",
            )
        ),
        command_orchestrate_default_max_modules=command_orchestrate_default_max_modules,
        command_orchestrate_default_strategy=env_get(
            "WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_STRATEGY",
            "balanced",
        ).strip(),
        command_orchestrate_restart_canceled_policy=_normalize_restart_canceled_policy(
            env_get(
                "WHERECODE_COMMAND_ORCHESTRATE_RESTART_CANCELED_POLICY",
                "off",
            )
        ),
        dev_routing_matrix_file=env_get(
            "WHERECODE_DEV_ROUTING_MATRIX_FILE",
            "control_center/capabilities/dev_routing_matrix.json",
        ).strip(),
        agent_rules_registry_file=env_get(
            "WHERECODE_AGENT_RULES_REGISTRY_FILE",
            "control_center/capabilities/agent_rules_registry.json",
        ).strip(),
        state_backend=env_get("WHERECODE_STATE_BACKEND", "memory").lower(),
        sqlite_path=env_get("WHERECODE_SQLITE_PATH", ".wherecode/state.db"),
        max_module_reflows=_parse_int(
            env_get("WHERECODE_MAX_MODULE_REFLOWS", "1"),
            default=1,
        ),
        release_approval_required=_parse_bool(
            env_get("WHERECODE_RELEASE_APPROVAL_REQUIRED", "false")
        ),
        role_routing_policy_file=env_get(
            "WHERECODE_ROLE_ROUTING_POLICY_FILE",
            ".agents/policies/role_routing.v3.json",
        ).strip(),
        metrics_alert_policy_file=env_get(
            "WHERECODE_METRICS_ALERT_POLICY_FILE",
            "control_center/metrics_alert_policy.json",
        ),
        metrics_alert_audit_file=env_get(
            "WHERECODE_METRICS_ALERT_AUDIT_FILE",
            ".wherecode/metrics_alert_policy_audit.jsonl",
        ),
        metrics_rollback_approval_file=env_get(
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE",
            ".wherecode/metrics_rollback_approvals.jsonl",
        ),
        metrics_rollback_approval_purge_audit_file=env_get(
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE",
            ".wherecode/metrics_rollback_approval_purge_audit.jsonl",
        ),
        allowed_origins_raw=env_get(
            "WHERECODE_ALLOWED_ORIGINS",
            "http://localhost:3000",
        ),
    )
