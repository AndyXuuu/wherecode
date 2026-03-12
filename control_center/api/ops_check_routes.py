from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from control_center.services import OpsCheckRuntime


def create_ops_check_router(*, ops_check_runtime: OpsCheckRuntime) -> APIRouter:
    router = APIRouter()

    @router.get("/ops/checks/scopes")
    def list_ops_check_scopes() -> dict[str, object]:
        return {"scopes": ops_check_runtime.list_scopes()}

    @router.get("/ops/checks/runs")
    def list_ops_check_runs(
        scope: str | None = None,
        run_status: str | None = None,
        limit: int = 20,
    ) -> dict[str, object]:
        return ops_check_runtime.list_runs(
            scope=scope,
            run_status=run_status,
            limit=limit,
        )

    @router.get("/ops/checks/latest")
    def get_latest_ops_check_run(scope: str | None = None) -> dict[str, object]:
        latest = ops_check_runtime.get_latest_run(scope=scope)
        if latest is None:
            raise HTTPException(status_code=404, detail="ops check run not found")
        return latest

    @router.get("/ops/checks/runs/{run_id}")
    def get_ops_check_run(run_id: str) -> dict[str, object]:
        snapshot = ops_check_runtime.get_run(run_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="ops check run not found")
        return snapshot

    @router.post("/ops/checks/runs", status_code=status.HTTP_201_CREATED)
    def create_ops_check_run(payload: dict[str, Any]) -> dict[str, object]:
        scope = str(payload.get("scope", "quick")).strip().lower()
        requested_by = str(payload.get("requested_by", "api")).strip() or "api"
        wait_raw = payload.get("wait_seconds", 0)
        try:
            wait_seconds = int(wait_raw)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="wait_seconds must be integer") from exc

        try:
            return ops_check_runtime.create_run(
                scope=scope,
                requested_by=requested_by,
                wait_seconds=max(wait_seconds, 0),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"create ops check run failed: {exc}") from exc

    return router
