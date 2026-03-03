from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


logger = logging.getLogger("wherecode.action_layer.agent_profile_loader")


@dataclass(frozen=True, slots=True)
class AgentProfile:
    role: str
    path: str
    profile_hash: str
    content: str


@dataclass(frozen=True, slots=True)
class AgentProfileAuditEvent:
    action: Literal["allow", "deny", "missing"]
    role: str
    requested_path: str
    resolved_path: str | None
    reason: str


class AgentProfileAccessError(PermissionError):
    def __init__(self, role: str, requested_path: str, allowed_path: str) -> None:
        super().__init__(
            f"agent profile access denied for role={role}: "
            f"requested={requested_path}, allowed={allowed_path}"
        )
        self.role = role
        self.requested_path = requested_path
        self.allowed_path = allowed_path


class AgentProfileNotFoundError(FileNotFoundError):
    def __init__(self, role: str, expected_path: str) -> None:
        super().__init__(f"agent profile not found for role={role}: {expected_path}")
        self.role = role
        self.expected_path = expected_path


class AgentProfileLoader:
    def __init__(self, profiles_root: str = "action_layer/agents") -> None:
        self._profiles_root = Path(profiles_root).resolve()
        self._audit_events: list[AgentProfileAuditEvent] = []

    @staticmethod
    def _normalize_role(role: str) -> str:
        if not isinstance(role, str):
            raise TypeError("role must be a string")
        normalized = role.strip().lower()
        if not normalized:
            raise ValueError("role must be a non-empty string")
        return normalized

    def _allowed_profile_path(self, role: str) -> Path:
        return (self._profiles_root / role / "agent.md").resolve()

    def _resolve_requested_path(self, role: str, requested_path: str | None) -> Path:
        if requested_path is None:
            return self._allowed_profile_path(role)

        requested = Path(requested_path)
        if not requested.is_absolute():
            requested = (self._profiles_root / requested).resolve()
        else:
            requested = requested.resolve()
        return requested

    def _record_event(
        self,
        action: Literal["allow", "deny", "missing"],
        role: str,
        requested_path: str,
        resolved_path: Path | None,
        reason: str,
    ) -> None:
        event = AgentProfileAuditEvent(
            action=action,
            role=role,
            requested_path=requested_path,
            resolved_path=str(resolved_path) if resolved_path else None,
            reason=reason,
        )
        self._audit_events.append(event)
        if action == "allow":
            logger.info(
                "agent_profile_access action=allow role=%s requested=%s resolved=%s reason=%s",
                role,
                requested_path,
                event.resolved_path,
                reason,
            )
            return
        logger.warning(
            "agent_profile_access action=%s role=%s requested=%s resolved=%s reason=%s",
            action,
            role,
            requested_path,
            event.resolved_path,
            reason,
        )

    def get_audit_events(self) -> list[AgentProfileAuditEvent]:
        return list(self._audit_events)

    def load(self, role: str, requested_path: str | None = None) -> AgentProfile:
        normalized_role = self._normalize_role(role)
        allowed = self._allowed_profile_path(normalized_role)
        requested = requested_path if requested_path is not None else str(allowed)
        resolved = self._resolve_requested_path(normalized_role, requested_path)

        if resolved != allowed:
            self._record_event(
                action="deny",
                role=normalized_role,
                requested_path=requested,
                resolved_path=resolved,
                reason="cross_role_or_custom_path_not_allowed",
            )
            raise AgentProfileAccessError(
                role=normalized_role,
                requested_path=requested,
                allowed_path=str(allowed),
            )

        if not allowed.is_file():
            self._record_event(
                action="missing",
                role=normalized_role,
                requested_path=requested,
                resolved_path=allowed,
                reason="profile_file_not_found",
            )
            raise AgentProfileNotFoundError(role=normalized_role, expected_path=str(allowed))

        content = allowed.read_text(encoding="utf-8")
        profile_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self._record_event(
            action="allow",
            role=normalized_role,
            requested_path=requested,
            resolved_path=allowed,
            reason="role_scoped_profile",
        )
        return AgentProfile(
            role=normalized_role,
            path=str(allowed),
            profile_hash=profile_hash,
            content=content,
        )
