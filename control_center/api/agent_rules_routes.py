from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from control_center.models import AgentRulesRegistryResponse
from control_center.services.agent_rules_registry import AgentRulesRegistryService


def create_agent_rules_router(
    *,
    agent_rules_registry_provider: Callable[[], AgentRulesRegistryService],
) -> APIRouter:
    router = APIRouter()

    def _registry() -> AgentRulesRegistryService:
        return agent_rules_registry_provider()

    @router.get("/agent-rules", response_model=AgentRulesRegistryResponse)
    async def get_agent_rules() -> AgentRulesRegistryResponse:
        return AgentRulesRegistryResponse(**_registry().export())

    @router.post("/agent-rules/reload", response_model=AgentRulesRegistryResponse)
    async def reload_agent_rules() -> AgentRulesRegistryResponse:
        try:
            payload = _registry().reload()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return AgentRulesRegistryResponse(**payload)

    return router
