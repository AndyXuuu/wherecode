from __future__ import annotations

import json
from pathlib import Path

import pytest

from control_center.services.agent_rules_registry import AgentRulesRegistryService


def test_agent_rules_registry_loads_default_file_when_missing(tmp_path: Path) -> None:
    registry_path = tmp_path / "agent_rules_registry.json"
    service = AgentRulesRegistryService(str(registry_path))

    assert registry_path.exists()
    exported = service.export()
    assert exported["version"] == "1"
    assert exported["total_roles"] >= 2
    assert "main" in exported["scopes"]
    assert "subproject" in exported["scopes"]


def test_agent_rules_registry_executor_mapping_respects_scope_order(tmp_path: Path) -> None:
    registry_path = tmp_path / "agent_rules_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": "1",
                "scopes": {
                    "main": [
                        {"role": "module-dev", "executor": "main-dev-agent"},
                        {"role": "chief-architect", "executor": "chief-agent"},
                    ],
                    "subproject": [
                        {"role": "module-dev", "executor": "sub-dev-agent"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    service = AgentRulesRegistryService(str(registry_path))
    mapping = service.executor_mapping(scopes=("subproject", "main"))
    assert mapping["module-dev"] == "sub-dev-agent"
    assert mapping["chief-architect"] == "chief-agent"


def test_agent_rules_registry_rejects_duplicate_role_in_scope(tmp_path: Path) -> None:
    registry_path = tmp_path / "agent_rules_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": "1",
                "scopes": {
                    "main": [
                        {"role": "chief-architect", "executor": "chief-a"},
                        {"role": "chief-architect", "executor": "chief-b"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        AgentRulesRegistryService(str(registry_path))
