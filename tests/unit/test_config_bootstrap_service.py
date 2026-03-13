from __future__ import annotations

from control_center.services.config_bootstrap import load_control_center_bootstrap_config


def _env_get_factory(values: dict[str, str]):
    def _env_get(key: str, default: str) -> str:
        return values.get(key, default)

    return _env_get


def test_config_bootstrap_defaults() -> None:
    config = load_control_center_bootstrap_config(_env_get_factory({}))
    assert config.log_level == "INFO"
    assert config.action_layer_timeout_seconds == 180.0
    assert config.action_layer_base_url == "http://127.0.0.1:8100"
    assert config.auth_enabled is True
    assert config.auth_token == "change-me"
    assert config.command_orchestrate_default_max_modules == 6
    assert config.command_orchestrate_default_strategy == "balanced"
    assert config.command_orchestrate_restart_canceled_policy == "off"
    assert (
        config.agent_rules_registry_file
        == "control_center/capabilities/agent_rules_registry.json"
    )
    assert config.role_routing_policy_file == ".agents/policies/role_routing.v3.json"
    assert config.state_backend == "memory"
    assert config.sqlite_path == ".wherecode/state.db"


def test_config_bootstrap_parsing_and_clamping() -> None:
    config = load_control_center_bootstrap_config(
        _env_get_factory(
            {
                "ACTION_LAYER_TIMEOUT_SECONDS": "12.5",
                "WHERECODE_AUTH_ENABLED": "false",
                "WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES": "100",
                "WHERECODE_COMMAND_ORCHESTRATE_PREFIXES": "/a,/b,,",
                "WHERECODE_COMMAND_ORCHESTRATE_RESTART_CANCELED_POLICY": "AUTO",
                "WHERECODE_METRICS_ALERT_POLICY_UPDATE_ROLES": "ops-admin, chief-architect",
                "WHERECODE_METRICS_ROLLBACK_APPROVER_ROLES": "release-manager,ops-admin",
                "WHERECODE_METRICS_ROLLBACK_APPROVAL_TTL_SECONDS": "bad-int",
                "WHERECODE_STATE_BACKEND": "SQLITE",
                "WHERECODE_MAX_MODULE_REFLOWS": "3",
                "WHERECODE_RELEASE_APPROVAL_REQUIRED": "true",
            }
        )
    )
    assert config.action_layer_timeout_seconds == 12.5
    assert config.auth_enabled is False
    assert config.command_orchestrate_default_max_modules == 20
    assert config.command_orchestrate_prefixes == ("/a", "/b")
    assert config.command_orchestrate_restart_canceled_policy == "auto_if_no_requirements"
    assert config.metrics_alert_policy_update_roles == {"ops-admin", "chief-architect"}
    assert config.metrics_rollback_approver_roles == {"release-manager", "ops-admin"}
    assert config.metrics_rollback_approval_ttl_seconds == 86400
    assert config.state_backend == "sqlite"
    assert config.max_module_reflows == 3
    assert config.release_approval_required is True
