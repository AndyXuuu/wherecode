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
