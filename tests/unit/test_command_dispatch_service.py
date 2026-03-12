from __future__ import annotations

import asyncio

from control_center.models import (
    ActionExecuteResponse,
    Command,
    Task,
)
from control_center.services.agent_router import AgentRoutingDecision
from control_center.services.command_dispatch import CommandDispatchService


class _FakeCommandPolicy:
    def __init__(self, result: ActionExecuteResponse | None) -> None:
        self._result = result
        self.called = 0

    async def maybe_execute(self, command: Command, task: Task) -> ActionExecuteResponse | None:
        _ = (command, task)
        self.called += 1
        return self._result


class _FakeAgentRouter:
    def __init__(self, decision: AgentRoutingDecision) -> None:
        self.decision = decision

    def route(self, task_assignee_agent: str, command_text: str) -> AgentRoutingDecision:
        _ = (task_assignee_agent, command_text)
        return self.decision


def _build_task_and_command() -> tuple[Task, Command]:
    task = Task(
        project_id="proj-1",
        title="task-1",
        assignee_agent="auto-agent",
    )
    command = Command(
        project_id=task.project_id,
        task_id=task.id,
        sequence=1,
        text="run test coverage",
        requested_by="owner",
    )
    return task, command


def test_command_dispatch_short_circuit_orchestrate_result() -> None:
    task, command = _build_task_and_command()
    policy = _FakeCommandPolicy(
        ActionExecuteResponse(
            status="success",
            summary="handled by command orchestration policy",
            agent="chief-architect",
            trace_id="act_policy_1",
        )
    )
    router = _FakeAgentRouter(
        AgentRoutingDecision(
            agent="coding-agent",
            reason="default_agent",
        )
    )
    called_requests: list[object] = []

    async def _execute_action(request):
        called_requests.append(request)
        return ActionExecuteResponse(
            status="success",
            summary="unexpected",
            agent="coding-agent",
            trace_id="act_unexpected",
        )

    service = CommandDispatchService(
        command_orchestration_policy_service_provider=lambda: policy,
        agent_router_provider=lambda: router,
        execute_action_handler=_execute_action,
    )

    result = asyncio.run(service.execute_command(command, task))
    assert result.summary == "handled by command orchestration policy"
    assert policy.called == 1
    assert called_requests == []


def test_command_dispatch_applies_routing_metadata_and_executes_action() -> None:
    task, command = _build_task_and_command()
    policy = _FakeCommandPolicy(None)
    router = _FakeAgentRouter(
        AgentRoutingDecision(
            agent="test-agent",
            reason="keyword_rule",
            matched_keyword="test",
            rule_id="rule_test_keywords",
        )
    )
    captured: list[object] = []

    async def _execute_action(request):
        captured.append(request)
        return ActionExecuteResponse(
            status="success",
            summary="executed",
            agent="test-agent",
            trace_id="act_routed_1",
        )

    service = CommandDispatchService(
        command_orchestration_policy_service_provider=lambda: policy,
        agent_router_provider=lambda: router,
        execute_action_handler=_execute_action,
    )

    result = asyncio.run(service.execute_command(command, task))
    assert result.status == "success"
    assert policy.called == 1
    assert command.metadata["routed_agent"] == "test-agent"
    assert command.metadata["routing_reason"] == "keyword_rule"
    assert command.metadata["routing_keyword"] == "test"
    assert command.metadata["routing_rule_id"] == "rule_test_keywords"
    assert len(captured) == 1
    request = captured[0]
    assert request.agent == "test-agent"
    assert request.text == command.text


def test_command_dispatch_clears_keyword_metadata_when_not_present() -> None:
    task, command = _build_task_and_command()
    command.metadata["routing_keyword"] = "old-keyword"
    command.metadata["routing_rule_id"] = "old-rule"

    policy = _FakeCommandPolicy(None)
    router = _FakeAgentRouter(
        AgentRoutingDecision(
            agent="coding-agent",
            reason="default_agent",
        )
    )

    async def _execute_action(_request):
        return ActionExecuteResponse(
            status="success",
            summary="executed",
            agent="coding-agent",
            trace_id="act_default_1",
        )

    service = CommandDispatchService(
        command_orchestration_policy_service_provider=lambda: policy,
        agent_router_provider=lambda: router,
        execute_action_handler=_execute_action,
    )

    _ = asyncio.run(service.execute_command(command, task))
    assert command.metadata["routed_agent"] == "coding-agent"
    assert command.metadata["routing_reason"] == "default_agent"
    assert "routing_keyword" not in command.metadata
    assert "routing_rule_id" not in command.metadata
