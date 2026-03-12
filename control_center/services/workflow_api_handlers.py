from __future__ import annotations

from collections.abc import Callable

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
    ExecuteWorkflowRunRequest,
    ExecuteWorkflowRunResponse,
    InterruptWorkflowRunRequest,
    InterruptWorkflowRunResponse,
    WorkflowRunOrchestrateLatestTelemetryResponse,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateRecoveryExecuteResponse,
    WorkflowRunOrchestrateRequest,
    WorkflowRunOrchestrateResponse,
    WorkflowRunRoutingDecisionsResponse,
)
from control_center.services.workflow_decompose_runtime import WorkflowDecomposeRuntimeService
from control_center.services.workflow_execution_runtime import WorkflowExecutionRuntimeService
from control_center.services.workflow_orchestration_runtime import (
    WorkflowOrchestrationRuntimeService,
)


class WorkflowAPIHandlersService:
    def __init__(
        self,
        *,
        workflow_decompose_runtime_service_provider: Callable[
            [], WorkflowDecomposeRuntimeService
        ],
        workflow_orchestration_runtime_service_provider: Callable[
            [], WorkflowOrchestrationRuntimeService
        ],
        workflow_execution_runtime_service_provider: Callable[
            [], WorkflowExecutionRuntimeService
        ],
    ) -> None:
        self._workflow_decompose_runtime_service_provider = (
            workflow_decompose_runtime_service_provider
        )
        self._workflow_orchestration_runtime_service_provider = (
            workflow_orchestration_runtime_service_provider
        )
        self._workflow_execution_runtime_service_provider = (
            workflow_execution_runtime_service_provider
        )

    async def decompose_bootstrap_workflow_run(
        self,
        run_id: str,
        payload: DecomposeBootstrapWorkflowRequest,
    ) -> DecomposeBootstrapWorkflowResponse:
        return await self._workflow_decompose_runtime_service_provider().decompose_bootstrap_workflow_run(
            run_id,
            payload,
        )

    async def get_decompose_bootstrap_pending(
        self,
        run_id: str,
    ) -> DecomposeBootstrapPendingWorkflowResponse:
        return await self._workflow_decompose_runtime_service_provider().get_decompose_bootstrap_pending(
            run_id,
        )

    async def get_decompose_bootstrap_aggregate_status(
        self,
        run_id: str,
    ) -> DecomposeBootstrapAggregateStatusResponse:
        return await self._workflow_decompose_runtime_service_provider().get_decompose_bootstrap_aggregate_status(
            run_id,
        )

    async def get_workflow_run_routing_decisions(
        self,
        run_id: str,
    ) -> WorkflowRunRoutingDecisionsResponse:
        return await self._workflow_decompose_runtime_service_provider().get_workflow_run_routing_decisions(
            run_id,
        )

    async def get_decompose_bootstrap_preview(
        self,
        run_id: str,
        refresh: bool = False,
    ) -> DecomposeBootstrapPreviewResponse:
        return await self._workflow_decompose_runtime_service_provider().get_decompose_bootstrap_preview(
            run_id,
            refresh,
        )

    async def advance_decompose_bootstrap_run(
        self,
        run_id: str,
        payload: DecomposeBootstrapAdvanceRequest,
    ) -> DecomposeBootstrapAdvanceResponse:
        return await self._workflow_decompose_runtime_service_provider().advance_decompose_bootstrap_run(
            run_id,
            payload,
        )

    async def advance_decompose_bootstrap_run_loop(
        self,
        run_id: str,
        payload: DecomposeBootstrapAdvanceLoopRequest,
    ) -> DecomposeBootstrapAdvanceLoopResponse:
        return await self._workflow_decompose_runtime_service_provider().advance_decompose_bootstrap_run_loop(
            run_id,
            payload,
        )

    async def confirm_decompose_bootstrap_workflow_run(
        self,
        run_id: str,
        payload: ConfirmDecomposeBootstrapWorkflowRequest,
    ) -> ConfirmDecomposeBootstrapWorkflowResponse:
        return await self._workflow_decompose_runtime_service_provider().confirm_decompose_bootstrap_workflow_run(
            run_id,
            payload,
        )

    async def orchestrate_workflow_run(
        self,
        run_id: str,
        payload: WorkflowRunOrchestrateRequest,
    ) -> WorkflowRunOrchestrateResponse:
        return await self._workflow_orchestration_runtime_service_provider().orchestrate_workflow_run(
            run_id,
            payload,
        )

    async def get_latest_orchestrate_telemetry(
        self,
        run_id: str,
    ) -> WorkflowRunOrchestrateLatestTelemetryResponse:
        return await self._workflow_orchestration_runtime_service_provider().get_latest_orchestrate_telemetry(
            run_id,
        )

    async def execute_orchestrate_recovery_action(
        self,
        run_id: str,
        payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
    ) -> WorkflowRunOrchestrateRecoveryExecuteResponse:
        return await self._workflow_orchestration_runtime_service_provider().execute_orchestrate_recovery_action(
            run_id,
            payload,
        )

    async def execute_workflow_run(
        self,
        run_id: str,
        payload: ExecuteWorkflowRunRequest,
    ) -> ExecuteWorkflowRunResponse:
        return await self._workflow_execution_runtime_service_provider().execute_workflow_run(
            run_id,
            payload,
        )

    async def interrupt_workflow_run(
        self,
        run_id: str,
        payload: InterruptWorkflowRunRequest,
    ) -> InterruptWorkflowRunResponse:
        return await self._workflow_execution_runtime_service_provider().interrupt_workflow_run(
            run_id,
            payload,
        )
