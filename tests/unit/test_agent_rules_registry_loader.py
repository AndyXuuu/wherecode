from __future__ import annotations

import json
from pathlib import Path

from action_layer.services.agent_rules_registry_loader import (
    build_registry_mapping_with_fallback,
    load_agent_registry_mapping_from_file,
)


def test_load_agent_registry_mapping_from_file_respects_scope_order(tmp_path: Path) -> None:
    registry_file = tmp_path / "agent_rules_registry.json"
    registry_file.write_text(
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

    mapping = load_agent_registry_mapping_from_file(
        str(registry_file),
        scope_order="subproject,main",
    )
    assert mapping["module-dev"] == "sub-dev-agent"
    assert mapping["chief-architect"] == "chief-agent"


def test_build_registry_mapping_with_fallback_returns_fallback_when_missing() -> None:
    fallback = {"module-dev": "coding-agent"}
    mapping = build_registry_mapping_with_fallback(
        "/non/existing/file.json",
        scope_order="subproject,main",
        fallback_mapping=fallback,
    )
    assert mapping == fallback
