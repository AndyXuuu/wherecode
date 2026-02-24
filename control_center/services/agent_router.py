from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentRoutingDecision:
    agent: str
    reason: str
    matched_keyword: str | None = None


class AgentRouter:
    def __init__(self, config_path: str) -> None:
        self._config_path = Path(config_path)
        self._default_agent = "coding-agent"
        self._rules: list[dict[str, object]] = []
        self._load_config()

    def _load_config(self) -> None:
        if not self._config_path.exists():
            self._set_default_rules()
            return

        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                self._set_default_rules()
                return
            default_agent = payload.get("default_agent")
            rules = payload.get("rules")
            if not isinstance(default_agent, str) or not default_agent.strip():
                default_agent = "coding-agent"
            if not isinstance(rules, list):
                rules = []

            normalized_rules: list[dict[str, object]] = []
            for item in rules:
                if not isinstance(item, dict):
                    continue
                agent = item.get("agent")
                keywords = item.get("keywords")
                if not isinstance(agent, str) or not agent.strip():
                    continue
                if not isinstance(keywords, list):
                    continue
                normalized_keywords = [
                    keyword.strip().lower()
                    for keyword in keywords
                    if isinstance(keyword, str) and keyword.strip()
                ]
                if not normalized_keywords:
                    continue
                normalized_rules.append(
                    {
                        "agent": agent.strip(),
                        "keywords": normalized_keywords,
                    }
                )
            self._default_agent = default_agent.strip()
            self._rules = normalized_rules
        except Exception:  # noqa: BLE001
            self._set_default_rules()

    def _set_default_rules(self) -> None:
        self._default_agent = "coding-agent"
        self._rules = [
            {
                "agent": "test-agent",
                "keywords": ["pytest", "unit test", "run tests", "integration test", "coverage", "test"],
            },
            {
                "agent": "review-agent",
                "keywords": ["review", "security", "audit", "risk"],
            },
        ]

    def select_agent(self, task_assignee_agent: str, command_text: str) -> str:
        return self.route(task_assignee_agent, command_text).agent

    def route(self, task_assignee_agent: str, command_text: str) -> AgentRoutingDecision:
        assignee = task_assignee_agent.strip().lower()
        if assignee and assignee not in {"auto", "auto-agent"}:
            return AgentRoutingDecision(
                agent=task_assignee_agent,
                reason="explicit_assignee",
            )

        lowered = command_text.lower()
        for rule in self._rules:
            keywords = rule["keywords"]
            for keyword in keywords:  # type: ignore[assignment]
                if keyword in lowered:
                    return AgentRoutingDecision(
                        agent=str(rule["agent"]),
                        reason="keyword_rule",
                        matched_keyword=str(keyword),
                    )
        return AgentRoutingDecision(
            agent=self._default_agent,
            reason="default_agent",
        )
