from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from control_center.executors.contracts import ExecutionStrategy


class RoleRoute(BaseModel):
    executor: str = "opencode"
    strategy: ExecutionStrategy = ExecutionStrategy.NATIVE
    agent: str | None = None
    category: str | None = None
    model: str | None = None


class RoleRoutingPolicyService:
    def __init__(self, policy_file: str) -> None:
        self._policy_file = Path(policy_file)
        self._mtime_ns: int | None = None
        self._default_route = RoleRoute()
        self._routes: dict[str, RoleRoute] = {}
        self.reload()

    def _load_json(self) -> dict[str, object]:
        payload = json.loads(self._policy_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("role routing policy must be a JSON object")
        return payload

    @staticmethod
    def _normalize_route(
        *,
        default_executor: str,
        default_strategy: ExecutionStrategy,
        raw: dict[str, object],
    ) -> RoleRoute:
        raw_executor = str(raw.get("executor", default_executor)).strip().lower()
        raw_strategy = str(raw.get("strategy", "")).strip().lower()
        if raw_executor == "ohmyopencode":
            raw_executor = "opencode"
            if not raw_strategy:
                raw_strategy = "ohmy"
        if raw_strategy not in {"native", "ohmy"}:
            raw_strategy = default_strategy.value
        return RoleRoute(
            executor=raw_executor or "opencode",
            strategy=ExecutionStrategy(raw_strategy),
            agent=(str(raw.get("agent")).strip() or None)
            if raw.get("agent") is not None
            else None,
            category=(str(raw.get("category")).strip() or None)
            if raw.get("category") is not None
            else None,
            model=(
                str(raw.get("model") or raw.get("model_tier")).strip() or None
                if raw.get("model") is not None or raw.get("model_tier") is not None
                else None
            ),
        )

    def reload(self) -> None:
        payload = self._load_json()
        roles_raw = payload.get("roles")
        if not isinstance(roles_raw, dict):
            raise ValueError("role routing policy missing 'roles' map")

        default_executor = str(payload.get("default_executor", "opencode")).strip().lower()
        raw_default_strategy = str(payload.get("default_strategy", "native")).strip().lower()
        default_strategy = (
            ExecutionStrategy.OHMY if raw_default_strategy == "ohmy" else ExecutionStrategy.NATIVE
        )

        default_route = RoleRoute(
            executor=default_executor or "opencode",
            strategy=default_strategy,
            model=(str(payload.get("default_model")).strip() or None)
            if payload.get("default_model") is not None
            else None,
        )
        routes: dict[str, RoleRoute] = {}
        for role, raw_value in roles_raw.items():
            if not isinstance(raw_value, dict):
                continue
            normalized_role = str(role).strip()
            if not normalized_role:
                continue
            routes[normalized_role] = self._normalize_route(
                default_executor=default_route.executor,
                default_strategy=default_route.strategy,
                raw=raw_value,
            )

        self._default_route = default_route
        self._routes = routes
        self._mtime_ns = self._policy_file.stat().st_mtime_ns

    def _reload_if_changed(self) -> None:
        current_mtime = self._policy_file.stat().st_mtime_ns
        if self._mtime_ns is None or current_mtime != self._mtime_ns:
            self.reload()

    def resolve(self, role: str) -> RoleRoute:
        self._reload_if_changed()
        normalized_role = role.strip()
        if not normalized_role:
            return self._default_route
        return self._routes.get(normalized_role, self._default_route)
