from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisteredAgent:
    role: str
    executor: str


class UnknownAgentRoleError(KeyError):
    def __init__(self, role: str) -> None:
        super().__init__(f"unknown agent role: {role}")
        self.role = role


class AgentRegistry:
    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self._mapping: dict[str, str] = {}
        source = mapping or self.default_mapping()
        for role, executor in source.items():
            self.register(role, executor, overwrite=True)

    @staticmethod
    def default_mapping() -> dict[str, str]:
        return {
            "chief-architect": "chief-architect-agent",
            "module-dev": "coding-agent",
            "doc-manager": "doc-agent",
            "qa-test": "test-agent",
            "integration-test": "test-agent",
            "security-review": "review-agent",
            "acceptance": "acceptance-agent",
            "release-manager": "release-agent",
        }

    @staticmethod
    def _normalize(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError(f"{field_name} must be a non-empty string")
        return normalized

    def register(self, role: str, executor: str, *, overwrite: bool = False) -> None:
        normalized_role = self._normalize(role, "role")
        normalized_executor = self._normalize(executor, "executor")

        if normalized_role in self._mapping and not overwrite:
            raise ValueError(f"role already registered: {normalized_role}")
        self._mapping[normalized_role] = normalized_executor

    def resolve(self, role: str) -> str:
        normalized_role = self._normalize(role, "role")
        if normalized_role not in self._mapping:
            raise UnknownAgentRoleError(normalized_role)
        return self._mapping[normalized_role]

    def get_registered_agent(self, role: str) -> RegisteredAgent:
        normalized_role = self._normalize(role, "role")
        return RegisteredAgent(role=normalized_role, executor=self.resolve(normalized_role))

    def has_role(self, role: str) -> bool:
        normalized_role = self._normalize(role, "role")
        return normalized_role in self._mapping

    def list_roles(self) -> list[str]:
        return sorted(self._mapping.keys())

    def as_dict(self) -> dict[str, str]:
        return dict(sorted(self._mapping.items()))
