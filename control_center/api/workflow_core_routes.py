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
    WorkflowRunArtifactsResponse,
    WorkflowRunReportResponse,
    WorkflowRunTimelineEvent,
    WorkflowRunTimelineResponse,
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

    def _run_gate_context(run: WorkflowRun) -> dict[str, object]:
        return {
            "current_stage": run.current_stage,
            "requirement_status": run.requirement_status,
            "clarification_rounds": run.clarification_rounds,
            "assumption_used": run.assumption_used,
            "blocked_reason": run.blocked_reason,
            "next_action_hint": run.next_action_hint,
            "accepted": run.accepted,
            "acceptance_evidence_complete": bool(
                run.metadata.get("acceptance_evidence_complete", False)
            ),
        }

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

    @router.get(
        "/v3/runs/{run_id}/timeline",
        response_model=WorkflowRunTimelineResponse,
    )
    async def get_run_timeline(run_id: str) -> WorkflowRunTimelineResponse:
        try:
            scheduler = _scheduler()
            run = scheduler.get_run(run_id)
            workitems = sorted(
                scheduler.list_workitems(run_id),
                key=lambda item: item.created_at,
            )
            gates = sorted(
                scheduler.list_gate_checks(run_id),
                key=lambda gate: gate.created_at,
            )
            artifacts = sorted(
                scheduler.list_artifacts(run_id),
                key=lambda artifact: artifact.created_at,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        events: list[WorkflowRunTimelineEvent] = [
            WorkflowRunTimelineEvent(
                ts=run.created_at,
                source="workflow_run",
                stage=str(run.current_stage.value),
                status=str(run.status.value),
                message="run created",
            )
        ]
        for workitem in workitems:
            events.append(
                WorkflowRunTimelineEvent(
                    ts=workitem.created_at,
                    source="workitem",
                    stage=workitem.role,
                    status=workitem.status.value,
                    message=f"{workitem.role} ({workitem.module_key or 'global'})",
                )
            )
        for gate in gates:
            events.append(
                WorkflowRunTimelineEvent(
                    ts=gate.created_at,
                    source="gate",
                    stage=gate.gate_type.value,
                    status=gate.status.value,
                    message=gate.summary or gate.gate_type.value,
                )
            )
        for artifact in artifacts:
            events.append(
                WorkflowRunTimelineEvent(
                    ts=artifact.created_at,
                    source="artifact",
                    stage=artifact.artifact_type.value,
                    status="created",
                    message=artifact.title,
                )
            )
        events = sorted(events, key=lambda event: event.ts)
        return WorkflowRunTimelineResponse(
            run_id=run.id,
            run_status=run.status,
            events=events,
            **_run_gate_context(run),
        )

    @router.get(
        "/v3/runs/{run_id}/artifacts",
        response_model=WorkflowRunArtifactsResponse,
    )
    async def get_run_artifacts_view(run_id: str) -> WorkflowRunArtifactsResponse:
        try:
            scheduler = _scheduler()
            run = scheduler.get_run(run_id)
            artifacts = scheduler.list_artifacts(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return WorkflowRunArtifactsResponse(
            run_id=run.id,
            run_status=run.status,
            artifacts=[item.model_dump(mode="json") for item in artifacts],
            **_run_gate_context(run),
        )

    @router.get(
        "/v3/runs/{run_id}/report",
        response_model=WorkflowRunReportResponse,
    )
    async def get_run_report(run_id: str) -> WorkflowRunReportResponse:
        try:
            scheduler = _scheduler()
            run = scheduler.get_run(run_id)
            workitems = scheduler.list_workitems(run_id)
            gates = scheduler.list_gate_checks(run_id)
            artifacts = scheduler.list_artifacts(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        workitem_counts: dict[str, int] = {}
        for item in workitems:
            key = item.status.value
            workitem_counts[key] = workitem_counts.get(key, 0) + 1

        gate_counts: dict[str, int] = {}
        for gate in gates:
            key = gate.status.value
            gate_counts[key] = gate_counts.get(key, 0) + 1

        artifact_counts: dict[str, int] = {}
        for artifact in artifacts:
            key = artifact.artifact_type.value
            artifact_counts[key] = artifact_counts.get(key, 0) + 1

        return WorkflowRunReportResponse(
            run_id=run.id,
            run_status=run.status,
            workitem_status_counts=workitem_counts,
            gate_status_counts=gate_counts,
            artifact_type_counts=artifact_counts,
            **_run_gate_context(run),
        )

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
