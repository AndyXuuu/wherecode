from __future__ import annotations

import json

from control_center.services.dev_routing_matrix import (
    DevRoutingMatrixService,
    normalize_task_routing,
)


def test_dev_routing_matrix_service_apply_adds_routing_fields(tmp_path) -> None:
    matrix_path = tmp_path / "dev_routing_matrix.json"
    matrix_path.write_text(
        json.dumps(
            {
                "version": "1",
                "default_target": {
                    "role": "module-dev",
                    "capability_id": "builtin.skill.general-dev",
                    "executor": "coding-agent",
                },
                "rules": [
                    {
                        "id": "data-rule",
                        "priority": 1,
                        "match": {
                            "domain": ["data"],
                            "task_type": ["feature"],
                        },
                        "target": {
                            "role": "module-dev",
                            "capability_id": "builtin.skill.data-pipeline",
                            "executor": "coding-agent",
                        },
                        "required_checks": ["backend-quick", "projects"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = DevRoutingMatrixService(str(matrix_path))

    modules = ["sentiment-crawl"]
    module_task_packages = {
        "sentiment-crawl": [
            {"role": "module-dev", "objective": "implement crawler"},
            {"role": "qa-test", "objective": "add tests"},
            {"role": "doc-manager", "objective": "update docs"},
            {"role": "security-review", "objective": "security pass"},
        ]
    }
    chief_metadata = {
        "decomposition": {
            "modules": [
                {
                    "module_key": "sentiment-crawl",
                    "coverage_tags": ["data", "crawl"],
                }
            ]
        }
    }

    routed_packages, decisions = service.apply(
        modules=modules,
        module_task_packages=module_task_packages,
        chief_metadata=chief_metadata,
    )

    decision = decisions["sentiment-crawl"]
    assert decision["rule_id"] == "data-rule"
    assert decision["target"]["capability_id"] == "builtin.skill.data-pipeline"

    module_dev = [
        item for item in routed_packages["sentiment-crawl"] if item["role"] == "module-dev"
    ][0]
    assert module_dev["routing"]["capability_id"] == "builtin.skill.data-pipeline"
    assert module_dev["routing"]["required_checks"] == ["backend-quick", "projects"]

    qa = [item for item in routed_packages["sentiment-crawl"] if item["role"] == "qa-test"][0]
    assert qa["routing"]["required_checks"] == ["backend-quick", "projects"]
    assert qa["routing"]["source_rule_id"] == "data-rule"


def test_normalize_task_routing_drops_empty_values() -> None:
    normalized = normalize_task_routing(
        {
            "rule_id": "data-rule",
            "capability_id": "builtin.skill.data-pipeline",
            "executor": "coding-agent",
            "required_checks": ["backend-quick", "", "backend-quick"],
            "handoff_roles": ["qa-test", "", "qa-test"],
            "signals": {
                "domain": ["data", "", "data"],
                "stack": [],
            },
        }
    )

    assert normalized["rule_id"] == "data-rule"
    assert normalized["required_checks"] == ["backend-quick"]
    assert normalized["handoff_roles"] == ["qa-test"]
    assert normalized["signals"] == {"domain": ["data"]}
