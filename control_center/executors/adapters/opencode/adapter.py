from __future__ import annotations

from collections.abc import Awaitable, Callable

from control_center.executors.contracts import (
    ExecutionError,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from control_center.executors.role_routing import RoleRoute
from control_center.models import ActionExecuteRequest, ActionExecuteResponse

ActionExecutor = Callable[[ActionExecuteRequest], Awaitable[ActionExecuteResponse]]


class OpenCodeAdapter:
    """Single OpenCode entrypoint with strategy routing (`native|ohmy`)."""

    def __init__(self, *, action_executor: ActionExecutor | None = None) -> None:
        self._action_executor = action_executor

    @staticmethod
    def _select_agent(route: RoleRoute, role: str) -> str | None:
        if route.agent:
            return route.agent
        if route.category:
            return f"{route.strategy.value}:{route.category}"
        if route.strategy.value == "ohmy":
            return f"ohmy:{role}"
        return None

    async def execute(
        self,
        request: ExecutionRequest,
        *,
        route: RoleRoute,
        project_id: str | None = None,
        requested_by: str | None = None,
        module_key: str | None = None,
    ) -> ExecutionResult:
        if self._action_executor is None:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                summary="opencode adapter is not configured",
                trace_id="opencode_unconfigured",
                error=ExecutionError(
                    code="EXECUTOR_NOT_CONFIGURED",
                    retryable=False,
                    message="action executor is not bound for opencode adapter",
                ),
                raw_ref="",
            )

        action_request = ActionExecuteRequest(
            text=request.text,
            agent=self._select_agent(route, request.role),
            requested_by=requested_by,
            task_id=request.task_id,
            project_id=project_id,
            role=request.role,
            module_key=module_key,
        )
        try:
            response = await self._action_executor(action_request)
        except Exception as exc:  # noqa: BLE001
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                summary=f"opencode execution failed: {exc}",
                trace_id="opencode_exec_error",
                error=ExecutionError(
                    code="OPENCODE_EXECUTION_ERROR",
                    retryable=True,
                    message=str(exc),
                ),
                raw_ref="",
            )

        status = ExecutionStatus.FAILED
        if response.status == "success":
            status = ExecutionStatus.SUCCESS
        elif response.status == "needs_discussion":
            status = ExecutionStatus.NEEDS_DISCUSSION

        error = None
        if status == ExecutionStatus.FAILED:
            error = ExecutionError(
                code="OPENCODE_FAILED",
                retryable=False,
                message=response.summary,
            )

        return ExecutionResult(
            status=status,
            summary=response.summary,
            trace_id=response.trace_id,
            error=error,
            raw_ref=f"action://{response.trace_id}",
        )
