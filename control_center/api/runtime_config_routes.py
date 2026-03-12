from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from control_center.models import CommandOrchestratePolicyConfigResponse


def create_runtime_config_router(
    *,
    command_orchestrate_policy_config_provider: Callable[[], dict[str, object]],
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/config/command-orchestrate-policy",
        response_model=CommandOrchestratePolicyConfigResponse,
    )
    async def get_command_orchestrate_policy_config() -> CommandOrchestratePolicyConfigResponse:
        payload = command_orchestrate_policy_config_provider()
        return CommandOrchestratePolicyConfigResponse(**payload)

    return router

