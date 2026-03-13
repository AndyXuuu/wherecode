from __future__ import annotations

from control_center.executors.adapters.opencode import OpenCodeAdapter
from control_center.executors.contracts import (
    ExecutionError,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionStrategy,
)
from control_center.executors.role_routing import RoleRoutingPolicyService
from control_center.models import WorkItem, WorkflowRun


class ExecutorService:
    """V3 execution service: single `opencode` adapter with dual strategy."""

    def __init__(
        self,
        *,
        role_routing_policy_file: str,
        action_executor=None,
        default_timeout_seconds: int = 180,
    ) -> None:
        self._role_routing = RoleRoutingPolicyService(role_routing_policy_file)
        self._opencode = OpenCodeAdapter(action_executor=action_executor)
        self._default_timeout_seconds = default_timeout_seconds

    async def execute_workitem(
        self,
        *,
        run: WorkflowRun,
        workitem: WorkItem,
        text: str,
    ) -> ExecutionResult:
        route = self._role_routing.resolve(workitem.role)
        if route.executor != "opencode":
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                summary=f"unsupported executor '{route.executor}' for role '{workitem.role}'",
                trace_id="executor_unsupported",
                error=ExecutionError(
                    code="UNSUPPORTED_EXECUTOR",
                    retryable=False,
                    message=f"role '{workitem.role}' routed to unsupported executor '{route.executor}'",
                ),
                raw_ref="",
            )

        request = ExecutionRequest(
            run_id=run.id,
            role=workitem.role,
            task_id=workitem.id,
            text=text,
            context_ref=f"workflow:{run.id}/module:{workitem.module_key or 'global'}",
            strategy=route.strategy,
            model=route.model,
            timeout_seconds=self._default_timeout_seconds,
        )
        return await self._opencode.execute(
            request,
            route=route,
            project_id=run.project_id,
            requested_by=run.requested_by,
            module_key=workitem.module_key,
        )

    def resolve_strategy(self, role: str) -> ExecutionStrategy:
        route = self._role_routing.resolve(role)
        return route.strategy
