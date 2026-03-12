from __future__ import annotations

from control_center.models import ActionExecuteResponse
from control_center.services import WorkflowDecomposeHelpersService


def test_build_chief_decompose_prompt_includes_required_coverage_tags() -> None:
    service = WorkflowDecomposeHelpersService()
    prompt = service.build_chief_decompose_prompt(
        requirements="A股 舆情 抓取、AI 解读、行业分析、题材分析并日报",
        max_modules=6,
        module_hints=["crawl-ingestion", "reporting-dashboard"],
        project_id="proj-1",
        task_id="task-1",
    )

    assert "project_id=proj-1" in prompt
    assert "task_id=task-1" in prompt
    assert "required_coverage_tags=" in prompt
    assert "crawl" in prompt
    assert "ai_interpret" in prompt
    assert "industry" in prompt
    assert "theme" in prompt
    assert "report" in prompt


def test_extract_modules_from_chief_response_prefers_metadata() -> None:
    service = WorkflowDecomposeHelpersService()
    response = ActionExecuteResponse(
        status="success",
        summary='{"modules":["ignored"]}',
        agent="chief-architect",
        trace_id="trace-1",
        metadata={
            "modules": ["alpha", "beta"],
            "decomposition": {"modules": [{"module_key": "gamma"}]},
        },
    )

    assert service.extract_modules_from_chief_response(response, 2) == ["alpha", "beta"]


def test_validate_requirement_module_mapping_reports_missing_and_invalid() -> None:
    service = WorkflowDecomposeHelpersService()
    mapping, missing, invalid, explicit = service.validate_requirement_module_mapping(
        ["crawl", "industry"],
        ["crawl-ingestion", "industry-analysis"],
        {
            "requirement_module_map": {
                "crawl": ["crawl-ingestion"],
                "industry": ["industry-analysis", "ghost-module"],
            }
        },
    )

    assert explicit is True
    assert missing == []
    assert mapping["crawl"] == ["crawl-ingestion"]
    assert mapping["industry"] == ["industry-analysis"]
    assert invalid == {"industry": ["ghost-module"]}


def test_validate_module_task_packages_falls_back_to_default_roles() -> None:
    service = WorkflowDecomposeHelpersService()
    packages, missing_modules, invalid_roles, missing_roles, explicit = (
        service.validate_module_task_packages(["sentiment-analysis"], {})
    )

    assert explicit is False
    assert missing_modules == []
    assert invalid_roles == {}
    assert missing_roles == {}
    roles = {item["role"] for item in packages["sentiment-analysis"]}
    assert roles == {"module-dev", "doc-manager", "qa-test", "security-review"}
