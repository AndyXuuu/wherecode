from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentRoutingDecision:
    agent: str
    reason: str
    matched_keyword: str | None = None
    rule_id: str | None = None


@dataclass(frozen=True, slots=True)
class AgentRule:
    rule_id: str
    agent: str
    keywords: tuple[str, ...]
    priority: int
    enabled: bool


class AgentRouter:
    def __init__(self, config_path: str) -> None:
        self._config_path = Path(config_path)
        self._default_agent = "coding-agent"
        self._rules: list[AgentRule] = []
        self._load_config()

    @property
    def default_agent(self) -> str:
        return self._default_agent

    @property
    def rules(self) -> list[AgentRule]:
        return list(self._rules)

    def reload(self) -> None:
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

            parsed_rules: list[tuple[int, AgentRule]] = []
            for index, item in enumerate(rules):
                if not isinstance(item, dict):
                    continue
                rule_id = item.get("id")
                agent = item.get("agent")
                keywords = item.get("keywords")
                if not isinstance(agent, str) or not agent.strip():
                    continue
                if not isinstance(keywords, list):
                    continue
                if not isinstance(rule_id, str) or not rule_id.strip():
                    rule_id = f"rule_{index + 1}_{agent.strip().replace(' ', '_')}"
                enabled = item.get("enabled", True)
                priority_raw = item.get("priority", 100)
                if not isinstance(enabled, bool):
                    enabled = True
                if not isinstance(priority_raw, int):
                    priority_raw = 100
                normalized_keywords = [
                    keyword.strip().lower()
                    for keyword in keywords
                    if isinstance(keyword, str) and keyword.strip()
                ]
                if not normalized_keywords:
                    continue
                parsed_rules.append(
                    (
                        index,
                        AgentRule(
                            rule_id=rule_id.strip(),
                            agent=agent.strip(),
                            keywords=tuple(normalized_keywords),
                            priority=priority_raw,
                            enabled=enabled,
                        ),
                    )
                )
            self._default_agent = default_agent.strip()
            self._rules = [
                rule
                for _, rule in sorted(
                    parsed_rules,
                    key=lambda pair: (pair[1].priority, pair[0]),
                )
            ]
        except Exception:  # noqa: BLE001
            self._set_default_rules()

    def _set_default_rules(self) -> None:
        self._default_agent = "coding-agent"
        self._rules = [
            AgentRule(
                rule_id="rule_test_keywords",
                agent="test-agent",
                keywords=("pytest", "unit test", "run tests", "integration test", "coverage", "test"),
                priority=10,
                enabled=True,
            ),
            AgentRule(
                rule_id="rule_review_keywords",
                agent="review-agent",
                keywords=("review", "security", "audit", "risk"),
                priority=20,
                enabled=True,
            ),
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
            if not rule.enabled:
                continue
            for keyword in rule.keywords:
                if keyword in lowered:
                    return AgentRoutingDecision(
                        agent=rule.agent,
                        reason="keyword_rule",
                        matched_keyword=str(keyword),
                        rule_id=rule.rule_id,
                    )
        return AgentRoutingDecision(
            agent=self._default_agent,
            reason="default_agent",
        )
