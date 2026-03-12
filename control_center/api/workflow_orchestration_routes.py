from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter

from control_center.models import (
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    DecomposeBootstrapAdvanceRequest,
    DecomposeBootstrapAdvanceResponse,
    DecomposeBootstrapAggregateStatusResponse,
    DecomposeBootstrapPendingWorkflowResponse,
    DecomposeBootstrapPreviewResponse,
    DecomposeBootstrapWorkflowRequest,
    DecomposeBootstrapWorkflowResponse,
    WorkflowRunOrchestrateLatestTelemetryResponse,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateRecoveryExecuteResponse,
    WorkflowRunOrchestrateRequest,
    WorkflowRunOrchestrateResponse,
    WorkflowRunRoutingDecisionsResponse,
)


def create_workflow_orchestration_router(
    *,
    decompose_bootstrap_handler: Callable[
        [str, DecomposeBootstrapWorkflowRequest], Awaitable[DecomposeBootstrapWorkflowResponse]
    ],
    decompose_pending_handler: Callable[
        [str], Awaitable[DecomposeBootstrapPendingWorkflowResponse]
    ],
    decompose_status_handler: Callable[
        [str], Awaitable[DecomposeBootstrapAggregateStatusResponse]
    ],
    routing_decisions_handler: Callable[
        [str], Awaitable[WorkflowRunRoutingDecisionsResponse]
    ],
    decompose_preview_handler: Callable[
        [str, bool], Awaitable[DecomposeBootstrapPreviewResponse]
    ],
    decompose_advance_handler: Callable[
        [str, DecomposeBootstrapAdvanceRequest], Awaitable[DecomposeBootstrapAdvanceResponse]
    ],
    decompose_advance_loop_handler: Callable[
        [str, DecomposeBootstrapAdvanceLoopRequest],
        Awaitable[DecomposeBootstrapAdvanceLoopResponse],
    ],
    decompose_confirm_handler: Callable[
        [str, ConfirmDecomposeBootstrapWorkflowRequest],
        Awaitable[ConfirmDecomposeBootstrapWorkflowResponse],
    ],
    orchestrate_handler: Callable[
        [str, WorkflowRunOrchestrateRequest], Awaitable[WorkflowRunOrchestrateResponse]
    ],
    orchestrate_latest_handler: Callable[
        [str], Awaitable[WorkflowRunOrchestrateLatestTelemetryResponse]
    ],
    orchestrate_recover_handler: Callable[
        [str, WorkflowRunOrchestrateRecoveryExecuteRequest],
        Awaitable[WorkflowRunOrchestrateRecoveryExecuteResponse],
    ],
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/v3/workflows/runs/{run_id}/decompose-bootstrap",
        response_model=DecomposeBootstrapWorkflowResponse,
    )
    async def decompose_bootstrap_workflow_run(
        run_id: str,
        payload: DecomposeBootstrapWorkflowRequest,
    ) -> DecomposeBootstrapWorkflowResponse:
        return await decompose_bootstrap_handler(run_id, payload)

    @router.get(
        "/v3/workflows/runs/{run_id}/decompose-bootstrap/pending",
        response_model=DecomposeBootstrapPendingWorkflowResponse,
    )
    async def get_decompose_bootstrap_pending(
        run_id: str,
    ) -> DecomposeBootstrapPendingWorkflowResponse:
        return await decompose_pending_handler(run_id)

    @router.get(
        "/v3/workflows/runs/{run_id}/decompose-bootstrap/status",
        response_model=DecomposeBootstrapAggregateStatusResponse,
    )
    async def get_decompose_bootstrap_aggregate_status(
        run_id: str,
    ) -> DecomposeBootstrapAggregateStatusResponse:
        return await decompose_status_handler(run_id)

    @router.get(
        "/v3/workflows/runs/{run_id}/routing-decisions",
        response_model=WorkflowRunRoutingDecisionsResponse,
    )
    async def get_workflow_run_routing_decisions(
        run_id: str,
    ) -> WorkflowRunRoutingDecisionsResponse:
        return await routing_decisions_handler(run_id)

    @router.get(
        "/v3/workflows/runs/{run_id}/decompose-bootstrap/preview",
        response_model=DecomposeBootstrapPreviewResponse,
    )
    async def get_decompose_bootstrap_preview(
        run_id: str,
        refresh: bool = False,
    ) -> DecomposeBootstrapPreviewResponse:
        return await decompose_preview_handler(run_id, refresh)

    @router.post(
        "/v3/workflows/runs/{run_id}/decompose-bootstrap/advance",
        response_model=DecomposeBootstrapAdvanceResponse,
    )
    async def advance_decompose_bootstrap_run(
        run_id: str,
        payload: DecomposeBootstrapAdvanceRequest,
    ) -> DecomposeBootstrapAdvanceResponse:
        return await decompose_advance_handler(run_id, payload)

    @router.post(
        "/v3/workflows/runs/{run_id}/decompose-bootstrap/advance-loop",
        response_model=DecomposeBootstrapAdvanceLoopResponse,
    )
    async def advance_decompose_bootstrap_run_loop(
        run_id: str,
        payload: DecomposeBootstrapAdvanceLoopRequest,
    ) -> DecomposeBootstrapAdvanceLoopResponse:
        return await decompose_advance_loop_handler(run_id, payload)

    @router.post(
        "/v3/workflows/runs/{run_id}/decompose-bootstrap/confirm",
        response_model=ConfirmDecomposeBootstrapWorkflowResponse,
    )
    async def confirm_decompose_bootstrap_workflow_run(
        run_id: str,
        payload: ConfirmDecomposeBootstrapWorkflowRequest,
    ) -> ConfirmDecomposeBootstrapWorkflowResponse:
        return await decompose_confirm_handler(run_id, payload)

    @router.post(
        "/v3/workflows/runs/{run_id}/orchestrate",
        response_model=WorkflowRunOrchestrateResponse,
    )
    async def orchestrate_workflow_run(
        run_id: str,
        payload: WorkflowRunOrchestrateRequest,
    ) -> WorkflowRunOrchestrateResponse:
        return await orchestrate_handler(run_id, payload)

    @router.get(
        "/v3/workflows/runs/{run_id}/orchestrate/latest",
        response_model=WorkflowRunOrchestrateLatestTelemetryResponse,
    )
    async def get_latest_orchestrate_telemetry(
        run_id: str,
    ) -> WorkflowRunOrchestrateLatestTelemetryResponse:
        return await orchestrate_latest_handler(run_id)

    @router.post(
        "/v3/workflows/runs/{run_id}/orchestrate/recover",
        response_model=WorkflowRunOrchestrateRecoveryExecuteResponse,
    )
    async def execute_orchestrate_recovery_action(
        run_id: str,
        payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
    ) -> WorkflowRunOrchestrateRecoveryExecuteResponse:
        return await orchestrate_recover_handler(run_id, payload)

    return router
