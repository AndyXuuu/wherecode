from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, HTTPException

from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionLayerHealthResponse,
)
from control_center.services import ActionLayerClientError


def create_action_layer_router(
    *,
    action_layer_health_handler: Callable[[], Awaitable[ActionLayerHealthResponse]],
    action_layer_execute_handler: Callable[
        [ActionExecuteRequest], Awaitable[ActionExecuteResponse]
    ],
) -> APIRouter:
    router = APIRouter()

    @router.get("/action-layer/health", response_model=ActionLayerHealthResponse)
    async def action_layer_health() -> ActionLayerHealthResponse:
        try:
            return await action_layer_health_handler()
        except ActionLayerClientError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("/action-layer/execute", response_model=ActionExecuteResponse)
    async def action_layer_execute(payload: ActionExecuteRequest) -> ActionExecuteResponse:
        try:
            return await action_layer_execute_handler(payload)
        except ActionLayerClientError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return router
