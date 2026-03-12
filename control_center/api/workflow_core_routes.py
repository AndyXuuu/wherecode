from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, status

from control_center.models import (
    ApproveWorkItemRequest,
    BootstrapWorkflowRequest,
    CompleteWorkItemRequest,
    CreateWorkflowRunRequest,
    CreateWorkItemRequest,
    RestartWorkflowRunRequest,
    RestartWorkflowRunResponse,
    Artifact,
    GateCheck,
    WorkflowRun,
    WorkItem,
)
from control_center.services import WorkflowEngine, WorkflowScheduler


def create_workflow_core_router(
    *,
    workflow_scheduler: WorkflowScheduler | None = None,
    workflow_engine: WorkflowEngine | None = None,
    workflow_scheduler_provider: Callable[[], WorkflowScheduler] | None = None,
    workflow_engine_provider: Callable[[], WorkflowEngine] | None = None,
) -> APIRouter:
    if workflow_scheduler is None and workflow_scheduler_provider is None:
        raise ValueError(
            "workflow scheduler is required for workflow core router initialization"
        )
    if workflow_engine is None and workflow_engine_provider is None:
        raise ValueError(
            "workflow engine is required for workflow core router initialization"
        )

    def _scheduler() -> WorkflowScheduler:
        if workflow_scheduler_provider is not None:
            return workflow_scheduler_provider()
        assert workflow_scheduler is not None
        return workflow_scheduler

    def _engine() -> WorkflowEngine:
        if workflow_engine_provider is not None:
            return workflow_engine_provider()
        assert workflow_engine is not None
        return workflow_engine

    router = APIRouter()

    @router.post(
        "/v3/workflows/runs",
        response_model=WorkflowRun,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_workflow_run(payload: CreateWorkflowRunRequest) -> WorkflowRun:
        return _scheduler().create_run(
            project_id=payload.project_id,
            task_id=payload.task_id,
            template_id=payload.template_id,
            requested_by=payload.requested_by,
            summary=payload.summary,
        )

    @router.get("/v3/workflows/runs/{run_id}", response_model=WorkflowRun)
    async def get_workflow_run(run_id: str) -> WorkflowRun:
        try:
            return _scheduler().get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post(
        "/v3/workflows/runs/{run_id}/restart",
        response_model=RestartWorkflowRunResponse,
    )
    async def restart_workflow_run(
        run_id: str,
        payload: RestartWorkflowRunRequest,
    ) -> RestartWorkflowRunResponse:
        try:
            restarted_run, copied_decomposition = _scheduler().restart_run(
                run_id=run_id,
                requested_by=payload.requested_by,
                reason=payload.reason,
                copy_decomposition=payload.copy_decomposition,
            )
            return RestartWorkflowRunResponse(
                source_run_id=run_id,
                restarted_run_id=restarted_run.id,
                restarted_run_status=restarted_run.status,
                copied_decomposition=copied_decomposition,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post(
        "/v3/workflows/runs/{run_id}/workitems",
        response_model=WorkItem,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_workitem(run_id: str, payload: CreateWorkItemRequest) -> WorkItem:
        try:
            return _scheduler().add_workitem(
                run_id=run_id,
                role=payload.role,
                module_key=payload.module_key,
                assignee_agent=payload.assignee_agent,
                depends_on=payload.depends_on,
                priority=payload.priority,
                requires_approval=payload.requires_approval,
                discussion_budget=payload.discussion_budget,
                discussion_timeout_seconds=payload.discussion_timeout_seconds,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/v3/workflows/runs/{run_id}/workitems", response_model=list[WorkItem])
    async def list_workitems(run_id: str) -> list[WorkItem]:
        try:
            return _scheduler().list_workitems(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/v3/workflows/runs/{run_id}/gates", response_model=list[GateCheck])
    async def list_workflow_gate_checks(run_id: str) -> list[GateCheck]:
        try:
            return _scheduler().list_gate_checks(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/v3/workflows/runs/{run_id}/artifacts", response_model=list[Artifact])
    async def list_workflow_artifacts(run_id: str) -> list[Artifact]:
        try:
            return _scheduler().list_artifacts(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/v3/workflows/runs/{run_id}/tick", response_model=list[WorkItem])
    async def tick_workflow_run(run_id: str) -> list[WorkItem]:
        try:
            return _scheduler().tick(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/v3/workflows/workitems/{workitem_id}/start", response_model=WorkItem)
    async def start_workitem(workitem_id: str) -> WorkItem:
        try:
            return _scheduler().start_workitem(workitem_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/v3/workflows/workitems/{workitem_id}/approve", response_model=WorkItem)
    async def approve_workitem(
        workitem_id: str,
        payload: ApproveWorkItemRequest,
    ) -> WorkItem:
        try:
            return _scheduler().approve_workitem(
                workitem_id,
                approved_by=payload.approved_by,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/v3/workflows/workitems/{workitem_id}/complete", response_model=WorkItem)
    async def complete_workitem(
        workitem_id: str,
        payload: CompleteWorkItemRequest,
    ) -> WorkItem:
        try:
            return _scheduler().complete_workitem(workitem_id, success=payload.success)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post(
        "/v3/workflows/runs/{run_id}/bootstrap",
        response_model=list[WorkItem],
    )
    async def bootstrap_workflow_run(
        run_id: str,
        payload: BootstrapWorkflowRequest,
    ) -> list[WorkItem]:
        try:
            result = _engine().bootstrap_standard_pipeline(run_id, payload.modules)
            return result.workitems
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
