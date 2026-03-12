from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, HTTPException

from control_center.models import (
    DiscussionSession,
    ExecuteWorkflowRunRequest,
    ExecuteWorkflowRunResponse,
    InterruptWorkflowRunRequest,
    InterruptWorkflowRunResponse,
    ResolveDiscussionRequest,
)
from control_center.services import WorkflowScheduler


def create_workflow_execution_router(
    *,
    execute_workflow_run_handler: Callable[
        [str, ExecuteWorkflowRunRequest], Awaitable[ExecuteWorkflowRunResponse]
    ],
    interrupt_workflow_run_handler: Callable[
        [str, InterruptWorkflowRunRequest], Awaitable[InterruptWorkflowRunResponse]
    ],
    workflow_scheduler: WorkflowScheduler | None = None,
    workflow_scheduler_provider: Callable[[], WorkflowScheduler] | None = None,
) -> APIRouter:
    if workflow_scheduler is None and workflow_scheduler_provider is None:
        raise ValueError(
            "workflow scheduler is required for workflow execution router initialization"
        )

    def _scheduler() -> WorkflowScheduler:
        if workflow_scheduler_provider is not None:
            return workflow_scheduler_provider()
        assert workflow_scheduler is not None
        return workflow_scheduler

    router = APIRouter()

    @router.post(
        "/v3/workflows/runs/{run_id}/execute",
        response_model=ExecuteWorkflowRunResponse,
    )
    async def execute_workflow_run(
        run_id: str,
        payload: ExecuteWorkflowRunRequest,
    ) -> ExecuteWorkflowRunResponse:
        return await execute_workflow_run_handler(run_id, payload)

    @router.post(
        "/v3/workflows/runs/{run_id}/interrupt",
        response_model=InterruptWorkflowRunResponse,
    )
    async def interrupt_workflow_run(
        run_id: str,
        payload: InterruptWorkflowRunRequest,
    ) -> InterruptWorkflowRunResponse:
        return await interrupt_workflow_run_handler(run_id, payload)

    @router.get(
        "/v3/workflows/workitems/{workitem_id}/discussions",
        response_model=list[DiscussionSession],
    )
    async def list_workitem_discussions(workitem_id: str) -> list[DiscussionSession]:
        try:
            return _scheduler().list_discussions(workitem_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post(
        "/v3/workflows/workitems/{workitem_id}/discussion/resolve",
        response_model=DiscussionSession,
    )
    async def resolve_workitem_discussion(
        workitem_id: str,
        payload: ResolveDiscussionRequest,
    ) -> DiscussionSession:
        try:
            return _scheduler().resolve_discussion(
                workitem_id,
                decision=payload.decision,
                resolved_by_role=payload.resolved_by,
                discussion_id=payload.discussion_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router
