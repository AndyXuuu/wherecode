from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request


class MetricsAuthorizationService:
    def __init__(
        self,
        *,
        auth_enabled_provider: Callable[[], bool],
        metrics_policy_update_roles_provider: Callable[[], set[str]],
        metrics_rollback_approver_roles_provider: Callable[[], set[str]],
    ) -> None:
        self._auth_enabled_provider = auth_enabled_provider
        self._metrics_policy_update_roles_provider = (
            metrics_policy_update_roles_provider
        )
        self._metrics_rollback_approver_roles_provider = (
            metrics_rollback_approver_roles_provider
        )

    @staticmethod
    def extract_request_token(request: Request) -> str | None:
        bearer = request.headers.get("Authorization", "")
        if bearer.startswith("Bearer "):
            return bearer[7:].strip()
        header_token = request.headers.get("X-WhereCode-Token")
        if header_token:
            return header_token.strip()
        return None

    @staticmethod
    def extract_request_role(request: Request) -> str | None:
        role = request.headers.get("X-WhereCode-Role", "").strip().lower()
        if role:
            return role
        return None

    def authorize_metrics_policy_update(
        self,
        request: Request,
        updated_by: str,
    ) -> str:
        normalized_updated_by = updated_by.strip().lower()
        if not self._auth_enabled_provider():
            return normalized_updated_by

        role = self.extract_request_role(request)
        if role is None:
            raise HTTPException(
                status_code=403,
                detail="missing role header: X-WhereCode-Role",
            )
        if role not in self._metrics_policy_update_roles_provider():
            raise HTTPException(
                status_code=403,
                detail=f"role not allowed: {role}",
            )
        if normalized_updated_by != role:
            raise HTTPException(
                status_code=409,
                detail="updated_by must match authenticated role",
            )
        return role

    def authorize_metrics_rollback_approval(
        self,
        request: Request,
        approved_by: str,
    ) -> str:
        normalized_approved_by = approved_by.strip().lower()
        if not self._auth_enabled_provider():
            return normalized_approved_by

        role = self.extract_request_role(request)
        if role is None:
            raise HTTPException(
                status_code=403,
                detail="missing role header: X-WhereCode-Role",
            )
        if role not in self._metrics_rollback_approver_roles_provider():
            raise HTTPException(
                status_code=403,
                detail=f"role not allowed: {role}",
            )
        if normalized_approved_by != role:
            raise HTTPException(
                status_code=409,
                detail="approved_by must match authenticated role",
            )
        return role
