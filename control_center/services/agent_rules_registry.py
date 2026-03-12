from __future__ import annotations

import json
import logging
from pathlib import Path


DEFAULT_AGENT_RULES_REGISTRY: dict[str, object] = {
    "version": "1",
    "updated_at": "2026-03-10T00:00:00Z",
    "scopes": {
        "main": [
            {
                "role": "chief-architect",
                "executor": "chief-architect-agent",
                "profile_path": "action_layer/agents/chief-architect/AGENTS.md",
                "description": "global planning and orchestration",
                "tags": ["planning", "architecture", "orchestration"],
            },
            {
                "role": "release-manager",
                "executor": "release-agent",
                "profile_path": "action_layer/agents/release-manager/AGENTS.md",
                "description": "release and acceptance closure",
                "tags": ["release", "acceptance"],
            },
        ],
        "subproject": [
            {
                "role": "module-dev",
                "executor": "coding-agent",
                "profile_path": "action_layer/agents/module-dev/AGENTS.md",
                "description": "feature/module implementation",
                "tags": ["coding", "implementation"],
            },
            {
                "role": "doc-manager",
                "executor": "doc-agent",
                "profile_path": "action_layer/agents/doc-manager/AGENTS.md",
                "description": "documentation sync and updates",
                "tags": ["docs"],
            },
            {
                "role": "qa-test",
                "executor": "test-agent",
                "profile_path": "action_layer/agents/qa-test/AGENTS.md",
                "description": "unit and integration test execution",
                "tags": ["testing"],
            },
            {
                "role": "security-review",
                "executor": "review-agent",
                "profile_path": "action_layer/agents/security-review/AGENTS.md",
                "description": "security and risk review",
                "tags": ["security", "review"],
            },
            {
                "role": "integration-test",
                "executor": "test-agent",
                "profile_path": "action_layer/agents/integration-test/AGENTS.md",
                "description": "cross-module integration validation",
                "tags": ["integration", "testing"],
            },
            {
                "role": "acceptance",
                "executor": "acceptance-agent",
                "profile_path": "action_layer/agents/acceptance/AGENTS.md",
                "description": "business acceptance validation",
                "tags": ["acceptance"],
            },
        ],
    },
}


class AgentRulesRegistryService:
    def __init__(
        self,
        registry_path: str,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._registry_path = Path(registry_path)
        self._logger = logger or logging.getLogger("wherecode.control_center.agent_rules")
        self._version = "1"
        self._updated_at: str | None = None
        self._scopes: dict[str, list[dict[str, object]]] = {}
        self.reload()

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value).strip().lower()

    def _write_default(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry_path.write_text(
            json.dumps(DEFAULT_AGENT_RULES_REGISTRY, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _load_payload(self) -> dict[str, object]:
        if not self._registry_path.exists():
            self._write_default()
        try:
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("agent rules load failed, fallback default: %s", exc)
            self._write_default()
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("agent rules registry must be object")
        return payload

    def _normalize_scope_rules(
        self,
        scope: str,
        records: object,
    ) -> list[dict[str, object]]:
        if not isinstance(records, list):
            raise ValueError(f"agent rules scope={scope} must be list")
        output: list[dict[str, object]] = []
        seen: set[str] = set()
        for item in records:
            if not isinstance(item, dict):
                continue
            role = self._normalize_text(item.get("role"))
            executor = self._normalize_text(item.get("executor"))
            if not role or not executor:
                continue
            if role in seen:
                raise ValueError(f"duplicate role in scope={scope}: {role}")
            seen.add(role)
            tags = item.get("tags")
            normalized_tags: list[str] = []
            if isinstance(tags, list):
                for raw in tags:
                    tag = self._normalize_text(raw)
                    if tag and tag not in normalized_tags:
                        normalized_tags.append(tag)
            profile_path_raw = item.get("profile_path")
            profile_path = str(profile_path_raw).strip() if profile_path_raw is not None else None
            description_raw = item.get("description")
            description = str(description_raw).strip() if description_raw is not None else None
            output.append(
                {
                    "role": role,
                    "executor": executor,
                    "scope": scope,
                    "profile_path": profile_path or None,
                    "description": description or None,
                    "tags": normalized_tags,
                }
            )
        return output

    def reload(self) -> dict[str, object]:
        payload = self._load_payload()
        version = str(payload.get("version", "1")).strip() or "1"
        updated_at_raw = payload.get("updated_at")
        updated_at = str(updated_at_raw).strip() if updated_at_raw is not None else None

        raw_scopes = payload.get("scopes")
        if not isinstance(raw_scopes, dict):
            raise ValueError("agent rules registry missing scopes object")

        normalized_scopes: dict[str, list[dict[str, object]]] = {}
        for raw_scope, records in raw_scopes.items():
            scope = self._normalize_text(raw_scope)
            if not scope:
                continue
            normalized_scopes[scope] = self._normalize_scope_rules(scope, records)

        self._version = version
        self._updated_at = updated_at
        self._scopes = normalized_scopes
        return self.export()

    def export(self) -> dict[str, object]:
        total_roles = sum(len(items) for items in self._scopes.values())
        return {
            "version": self._version,
            "updated_at": self._updated_at,
            "source_path": str(self._registry_path),
            "scopes": {key: list(value) for key, value in self._scopes.items()},
            "total_roles": total_roles,
        }

    def executor_mapping(
        self,
        *,
        scopes: tuple[str, ...] = ("subproject", "main"),
    ) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for scope in scopes:
            records = self._scopes.get(self._normalize_text(scope), [])
            for item in records:
                role = str(item.get("role", "")).strip()
                executor = str(item.get("executor", "")).strip()
                if role and executor and role not in mapping:
                    mapping[role] = executor
        return mapping

    def list_roles(self, scope: str | None = None) -> list[str]:
        if scope is not None:
            records = self._scopes.get(self._normalize_text(scope), [])
            return sorted({str(item.get("role", "")).strip() for item in records if item.get("role")})
        roles: set[str] = set()
        for records in self._scopes.values():
            for item in records:
                role = str(item.get("role", "")).strip()
                if role:
                    roles.add(role)
        return sorted(roles)
