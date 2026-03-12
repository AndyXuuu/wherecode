from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from control_center.services.app_wiring import (
    build_ops_check_runtime,
    configure_control_center_middlewares,
    resolve_allowed_origins,
)


def _build_test_app(*, auth_enabled: bool) -> FastAPI:
    app = FastAPI()
    configure_control_center_middlewares(
        app,
        allowed_origins=["http://localhost:3000"],
        logger=logging.getLogger("test.app_wiring"),
        auth_enabled_provider=lambda: auth_enabled,
        auth_token_provider=lambda: "test-token",
        auth_whitelist_prefixes=("/healthz",),
        extract_request_token=lambda request: request.headers.get("X-WhereCode-Token"),
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/secure")
    def secure(request: Request) -> dict[str, str]:
        request_id = str(getattr(request.state, "request_id", ""))
        return {"status": "ok", "request_id": request_id}

    return app


def test_resolve_allowed_origins_filters_empty_items() -> None:
    origins = resolve_allowed_origins(" http://a.com, ,http://b.com ,,")
    assert origins == ["http://a.com", "http://b.com"]


def test_auth_middleware_blocks_and_allows_secure_endpoint() -> None:
    client = TestClient(_build_test_app(auth_enabled=True))

    missing = client.get("/secure")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "unauthorized"

    allowed = client.get("/secure", headers={"X-WhereCode-Token": "test-token"})
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "ok"
    assert allowed.headers.get("X-Request-Id", "").startswith("req_")


def test_auth_middleware_keeps_healthz_whitelisted() -> None:
    client = TestClient(_build_test_app(auth_enabled=True))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_build_ops_check_runtime_uses_root_relative_defaults() -> None:
    runtime = build_ops_check_runtime(
        state_store=None,
        root_dir=Path("/tmp/wherecode"),
        env_get=lambda _key, default: default,
    )
    assert runtime._script_path == Path("/tmp/wherecode/scripts/check_all_local.sh")
    assert runtime._log_dir == Path("/tmp/wherecode/.wherecode/check_runs")
    assert runtime._report_dir == Path("/tmp/wherecode/docs/v2_reports/check_runs")
