from __future__ import annotations

from pathlib import Path

from control_center.services import AgentRouter


def test_agent_router_uses_explicit_task_assignee(tmp_path: Path) -> None:
    config_path = tmp_path / "agents.routing.json"
    config_path.write_text(
        """
{
  "default_agent": "coding-agent",
  "rules": [
    {"agent": "test-agent", "keywords": ["pytest"]}
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    router = AgentRouter(str(config_path))
    selected = router.select_agent("review-agent", "run pytest")
    assert selected == "review-agent"
    decision = router.route("review-agent", "run pytest")
    assert decision.rule_id is None


def test_agent_router_routes_auto_agent_by_keyword(tmp_path: Path) -> None:
    config_path = tmp_path / "agents.routing.json"
    config_path.write_text(
        """
{
  "default_agent": "coding-agent",
  "rules": [
    {"agent": "test-agent", "keywords": ["pytest", "unit test"]},
    {"agent": "review-agent", "keywords": ["security", "review"]}
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    router = AgentRouter(str(config_path))
    assert router.select_agent("auto-agent", "please run pytest for auth") == "test-agent"
    assert router.select_agent("auto-agent", "security review this patch") == "review-agent"
    assert router.select_agent("auto-agent", "implement login ui") == "coding-agent"

    route_test = router.route("auto-agent", "please run pytest for auth")
    assert route_test.reason == "keyword_rule"
    assert route_test.matched_keyword == "pytest"
    assert route_test.rule_id == "rule_1_test-agent"

    route_default = router.route("auto-agent", "implement login ui")
    assert route_default.reason == "default_agent"
    assert route_default.matched_keyword is None
    assert route_default.rule_id is None


def test_agent_router_respects_rule_priority_and_enabled(tmp_path: Path) -> None:
    config_path = tmp_path / "agents.routing.json"
    config_path.write_text(
        """
{
  "default_agent": "coding-agent",
  "rules": [
    {"id": "review_rule", "agent": "review-agent", "priority": 20, "enabled": true, "keywords": ["test"]},
    {"id": "test_rule", "agent": "test-agent", "priority": 5, "enabled": true, "keywords": ["test"]},
    {"agent": "disabled-agent", "priority": 1, "enabled": false, "keywords": ["test"]}
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    router = AgentRouter(str(config_path))
    decision = router.route("auto-agent", "please test this flow")
    assert decision.agent == "test-agent"
    assert decision.reason == "keyword_rule"
    assert decision.matched_keyword == "test"
    assert decision.rule_id == "test_rule"
