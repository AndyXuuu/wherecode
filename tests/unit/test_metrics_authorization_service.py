from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from control_center.services.metrics_authorization import MetricsAuthorizationService


def _build_request(headers: dict[str, str]) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in headers.items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
    }
    return Request(scope)


def _build_service(*, auth_enabled: bool) -> MetricsAuthorizationService:
    return MetricsAuthorizationService(
        auth_enabled_provider=lambda: auth_enabled,
        metrics_policy_update_roles_provider=lambda: {"ops-admin", "chief-architect"},
        metrics_rollback_approver_roles_provider=lambda: {"ops-admin", "release-manager"},
    )


def test_metrics_authorization_policy_update_allows_when_auth_disabled() -> None:
    service = _build_service(auth_enabled=False)
    request = _build_request({})

    actor = service.authorize_metrics_policy_update(request, "Ops-Admin")
    assert actor == "ops-admin"


def test_metrics_authorization_policy_update_requires_role_header_when_enabled() -> None:
    service = _build_service(auth_enabled=True)
    request = _build_request({})

    with pytest.raises(HTTPException) as exc:
        service.authorize_metrics_policy_update(request, "ops-admin")
    assert exc.value.status_code == 403
    assert "missing role header" in str(exc.value.detail)


def test_metrics_authorization_policy_update_rejects_role_mismatch() -> None:
    service = _build_service(auth_enabled=True)
    request = _build_request({"X-WhereCode-Role": "ops-admin"})

    with pytest.raises(HTTPException) as exc:
        service.authorize_metrics_policy_update(request, "chief-architect")
    assert exc.value.status_code == 409
    assert "updated_by must match authenticated role" in str(exc.value.detail)


def test_metrics_authorization_policy_update_accepts_allowed_role() -> None:
    service = _build_service(auth_enabled=True)
    request = _build_request({"X-WhereCode-Role": "chief-architect"})

    actor = service.authorize_metrics_policy_update(request, "chief-architect")
    assert actor == "chief-architect"


def test_metrics_authorization_rollback_approval_rejects_unauthorized_role() -> None:
    service = _build_service(auth_enabled=True)
    request = _build_request({"X-WhereCode-Role": "qa-test"})

    with pytest.raises(HTTPException) as exc:
        service.authorize_metrics_rollback_approval(request, "qa-test")
    assert exc.value.status_code == 403
    assert "role not allowed" in str(exc.value.detail)


def test_metrics_authorization_extract_request_token_supports_bearer_and_header() -> None:
    bearer_request = _build_request({"Authorization": "Bearer abc123"})
    header_request = _build_request({"X-WhereCode-Token": "xyz789"})
    empty_request = _build_request({})

    assert MetricsAuthorizationService.extract_request_token(bearer_request) == "abc123"
    assert MetricsAuthorizationService.extract_request_token(header_request) == "xyz789"
    assert MetricsAuthorizationService.extract_request_token(empty_request) is None
