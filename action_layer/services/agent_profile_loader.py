from __future__ import annotations

import hashlib
import logging
import os
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
    _STANDARD_PROFILE_FILE = "AGENTS.md"
    _LEGACY_PROFILE_FILE = "agent.md"

    def __init__(
        self,
        profiles_root: str = ".agents/roles",
        fallback_roots: tuple[str, ...] | None = ("action_layer/agents",),
    ) -> None:
        self._profiles_roots = self._normalize_roots(
            profiles_root=profiles_root,
            fallback_roots=fallback_roots,
        )
        self._audit_events: list[AgentProfileAuditEvent] = []

    @staticmethod
    def _split_roots(value: str) -> list[str]:
        normalized = value.replace(",", os.pathsep)
        return [part.strip() for part in normalized.split(os.pathsep) if part.strip()]

    def _normalize_roots(
        self,
        *,
        profiles_root: str,
        fallback_roots: tuple[str, ...] | None,
    ) -> tuple[Path, ...]:
        roots: list[Path] = []
        seen: set[str] = set()
        tokens: list[str] = self._split_roots(profiles_root)
        if fallback_roots:
            for fallback in fallback_roots:
                tokens.extend(self._split_roots(fallback))
        if not tokens:
            tokens = [".agents/roles", "action_layer/agents"]

        for token in tokens:
            resolved = Path(token).resolve()
            key = str(resolved)
            if key in seen:
                continue
            roots.append(resolved)
            seen.add(key)
        return tuple(roots)

    @staticmethod
    def _normalize_role(role: str) -> str:
        if not isinstance(role, str):
            raise TypeError("role must be a string")
        normalized = role.strip().lower()
        if not normalized:
            raise ValueError("role must be a non-empty string")
        return normalized

    def _allowed_profile_paths(self, role: str) -> tuple[Path, ...]:
        candidates: list[Path] = []
        for root in self._profiles_roots:
            role_root = (root / role).resolve()
            candidates.append((role_root / self._STANDARD_PROFILE_FILE).resolve())
            candidates.append((role_root / self._LEGACY_PROFILE_FILE).resolve())
        return tuple(candidates)

    def _default_profile_path(self, role: str) -> Path:
        for candidate in self._allowed_profile_paths(role):
            if candidate.is_file():
                return candidate
        return self._allowed_profile_paths(role)[0]

    def _resolve_requested_path(
        self,
        role: str,
        requested_path: str | None,
        allowed_paths: tuple[Path, ...],
    ) -> Path:
        if requested_path is None:
            return self._default_profile_path(role)

        requested = Path(requested_path)
        if requested.is_absolute():
            requested = requested.resolve()
            return requested

        for root in self._profiles_roots:
            candidate = (root / requested).resolve()
            if candidate in allowed_paths and candidate.is_file():
                return candidate
        for root in self._profiles_roots:
            candidate = (root / requested).resolve()
            if candidate in allowed_paths:
                return candidate
        primary_root = self._profiles_roots[0]
        return (primary_root / requested).resolve()

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
        allowed_paths = self._allowed_profile_paths(normalized_role)
        default_allowed = self._default_profile_path(normalized_role)
        requested = requested_path if requested_path is not None else str(default_allowed)
        resolved = self._resolve_requested_path(
            normalized_role, requested_path, allowed_paths
        )

        if resolved not in allowed_paths:
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
                allowed_path=" | ".join(str(path) for path in allowed_paths),
            )

        if not resolved.is_file():
            self._record_event(
                action="missing",
                role=normalized_role,
                requested_path=requested,
                resolved_path=resolved,
                reason="profile_file_not_found",
            )
            raise AgentProfileNotFoundError(role=normalized_role, expected_path=str(resolved))

        content = resolved.read_text(encoding="utf-8")
        profile_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self._record_event(
            action="allow",
            role=normalized_role,
            requested_path=requested,
            resolved_path=resolved,
            reason="role_scoped_profile",
        )
        return AgentProfile(
            role=normalized_role,
            path=str(resolved),
            profile_hash=profile_hash,
            content=content,
        )
