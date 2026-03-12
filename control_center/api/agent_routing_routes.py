from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from control_center.models import AgentRoutingConfigResponse, AgentRoutingConfigUpdateRequest
from control_center.services import AgentRouter


def create_agent_routing_router(
    *,
    agent_router: AgentRouter | None = None,
    agent_router_provider: Callable[[], AgentRouter] | None = None,
) -> APIRouter:
    if agent_router is None and agent_router_provider is None:
        raise ValueError("agent router is required for agent-routing router initialization")

    def _agent_router() -> AgentRouter:
        if agent_router_provider is not None:
            return agent_router_provider()
        assert agent_router is not None
        return agent_router

    def _build_routing_config_response() -> AgentRoutingConfigResponse:
        config = _agent_router().get_config()
        return AgentRoutingConfigResponse(
            default_agent=str(config["default_agent"]),
            rules=[
                {
                    "id": str(item["id"]),
                    "agent": str(item["agent"]),
                    "priority": int(item["priority"]),
                    "enabled": bool(item["enabled"]),
                    "keywords": list(item["keywords"]),
                }
                for item in config["rules"]
                if isinstance(item, dict)
            ],
        )

    router = APIRouter()

    @router.get("/agent-routing", response_model=AgentRoutingConfigResponse)
    async def get_agent_routing() -> AgentRoutingConfigResponse:
        return _build_routing_config_response()

    @router.put("/agent-routing", response_model=AgentRoutingConfigResponse)
    async def update_agent_routing(
        payload: AgentRoutingConfigUpdateRequest,
    ) -> AgentRoutingConfigResponse:
        _agent_router().update_config(
            default_agent=payload.default_agent,
            rules=[
                {
                    "id": rule.id,
                    "agent": rule.agent,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "keywords": list(rule.keywords),
                }
                for rule in payload.rules
            ],
        )
        return _build_routing_config_response()

    @router.post("/agent-routing/reload", response_model=AgentRoutingConfigResponse)
    async def reload_agent_routing() -> AgentRoutingConfigResponse:
        _agent_router().reload()
        return _build_routing_config_response()

    return router
