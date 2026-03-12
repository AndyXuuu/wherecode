from __future__ import annotations

from collections.abc import Awaitable, Callable

from control_center.models import ActionExecuteRequest, ActionExecuteResponse, Command, Task
from control_center.services.agent_router import AgentRouter, AgentRoutingDecision
from control_center.services.command_orchestration_policy import (
    CommandOrchestrationPolicyService,
)


class CommandDispatchService:
    def __init__(
        self,
        *,
        command_orchestration_policy_service_provider: Callable[
            [], CommandOrchestrationPolicyService
        ],
        agent_router_provider: Callable[[], AgentRouter],
        execute_action_handler: Callable[
            [ActionExecuteRequest], Awaitable[ActionExecuteResponse]
        ],
    ) -> None:
        self._command_orchestration_policy_service_provider = (
            command_orchestration_policy_service_provider
        )
        self._agent_router_provider = agent_router_provider
        self._execute_action_handler = execute_action_handler

    @staticmethod
    def _apply_routing_metadata(
        command: Command,
        routing: AgentRoutingDecision,
    ) -> None:
        command.metadata["routed_agent"] = routing.agent
        command.metadata["routing_reason"] = routing.reason
        if routing.matched_keyword is not None:
            command.metadata["routing_keyword"] = routing.matched_keyword
        else:
            command.metadata.pop("routing_keyword", None)
        if routing.rule_id is not None:
            command.metadata["routing_rule_id"] = routing.rule_id
        else:
            command.metadata.pop("routing_rule_id", None)

    async def execute_command(
        self,
        command: Command,
        task: Task,
    ) -> ActionExecuteResponse:
        orchestrate_result = await self._command_orchestration_policy_service_provider().maybe_execute(
            command,
            task,
        )
        if orchestrate_result is not None:
            return orchestrate_result

        routing = self._agent_router_provider().route(task.assignee_agent, command.text)
        self._apply_routing_metadata(command, routing)
        return await self._execute_action_handler(
            ActionExecuteRequest(
                text=command.text,
                agent=routing.agent,
                requested_by=command.requested_by,
                task_id=command.task_id,
                project_id=command.project_id,
            )
        )

    async def execute_workitem(
        self,
        request: ActionExecuteRequest,
    ) -> ActionExecuteResponse:
        return await self._execute_action_handler(request)
