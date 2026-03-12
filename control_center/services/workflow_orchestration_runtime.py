from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

from fastapi import HTTPException

from control_center.models import (
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapAggregateStatusResponse,
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    DecomposeBootstrapPreviewResponse,
    DecomposeBootstrapWorkflowRequest,
    DecomposeBootstrapWorkflowResponse,
    ExecuteWorkflowRunRequest,
    ExecuteWorkflowRunResponse,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowRunOrchestrateDecisionReport,
    WorkflowRunOrchestrateDecomposePayload,
    WorkflowRunOrchestrateDecompositionSummary,
    WorkflowRunOrchestrateExecutionProfile,
    WorkflowRunOrchestrateLatestTelemetryResponse,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateRecoveryExecuteResponse,
    WorkflowRunOrchestrateRequest,
    WorkflowRunOrchestrateResponse,
    WorkflowRunOrchestrateStrategy,
    WorkflowRunOrchestrateTelemetryRecord,
    WorkflowRunOrchestrateTelemetrySnapshot,
)
from control_center.services.workflow_orchestration_runtime_policy import (
    build_orchestrate_execute_request,
    build_recovery_advance_loop_request,
    build_recovery_execute_request,
    build_recovery_orchestrate_request,
    build_recovery_response,
    derive_execution_profile,
    resolve_decompose_payload,
    resolve_latest_confirmation_token,
)
from control_center.services.workflow_scheduler import WorkflowScheduler


class WorkflowOrchestrationRuntimeService:
    def __init__(
        self,
        *,
        workflow_scheduler_provider: Callable[[], WorkflowScheduler],
        now_utc_handler: Callable[[], datetime],
        optional_text_handler: Callable[[object], str | None],
        build_decompose_aggregate_status_handler: Callable[
            [str, WorkflowRun], DecomposeBootstrapAggregateStatusResponse
        ],
        build_orchestrate_decomposition_summary_handler: Callable[
            [WorkflowRun, DecomposeBootstrapAggregateStatusResponse],
            WorkflowRunOrchestrateDecompositionSummary,
        ],
        build_orchestrate_decision_report_handler: Callable[
            [
                str,
                WorkflowRunOrchestrateStrategy,
                WorkflowRunOrchestrateExecutionProfile,
                str,
                str | None,
                list[str],
                DecomposeBootstrapAggregateStatusResponse,
                DecomposeBootstrapAggregateStatusResponse,
            ],
            WorkflowRunOrchestrateDecisionReport,
        ],
        build_orchestrate_telemetry_snapshot_handler: Callable[
            [
                datetime,
                datetime,
                list[str],
                DecomposeBootstrapAggregateStatusResponse,
                DecomposeBootstrapAggregateStatusResponse,
                ExecuteWorkflowRunResponse | None,
            ],
            WorkflowRunOrchestrateTelemetrySnapshot,
        ],
        read_orchestrate_latest_record_handler: Callable[
            [WorkflowRun], WorkflowRunOrchestrateTelemetryRecord | None
        ],
        persist_orchestrate_latest_record_handler: Callable[
            [
                str,
                WorkflowRun,
                WorkflowRunOrchestrateStrategy,
                str,
                str | None,
                list[str],
                WorkflowRunOrchestrateDecisionReport,
                WorkflowRunOrchestrateTelemetrySnapshot,
            ],
            None,
        ],
        resolve_orchestrate_recovery_action_handler: Callable[
            [
                WorkflowRunOrchestrateRecoveryExecuteRequest,
                WorkflowRunOrchestrateTelemetryRecord | None,
            ],
            tuple[str | None, str],
        ],
        get_pending_decomposition_handler: Callable[[WorkflowRun], dict[str, object] | None],
        get_pending_confirmation_status_handler: Callable[[dict[str, object]], str],
        decompose_bootstrap_workflow_run_handler: Callable[
            [str, DecomposeBootstrapWorkflowRequest],
            Awaitable[DecomposeBootstrapWorkflowResponse],
        ],
        execute_workflow_run_handler: Callable[
            [str, ExecuteWorkflowRunRequest],
            Awaitable[ExecuteWorkflowRunResponse],
        ],
        get_decompose_bootstrap_preview_handler: Callable[
            [str, bool], Awaitable[DecomposeBootstrapPreviewResponse]
        ],
        confirm_decompose_bootstrap_workflow_run_handler: Callable[
            [str, ConfirmDecomposeBootstrapWorkflowRequest],
            Awaitable[ConfirmDecomposeBootstrapWorkflowResponse],
        ],
        advance_decompose_bootstrap_run_loop_handler: Callable[
            [str, DecomposeBootstrapAdvanceLoopRequest],
            Awaitable[DecomposeBootstrapAdvanceLoopResponse],
        ],
    ) -> None:
        self._workflow_scheduler_provider = workflow_scheduler_provider
        self._now_utc_handler = now_utc_handler
        self._optional_text_handler = optional_text_handler
        self._build_decompose_aggregate_status_handler = (
            build_decompose_aggregate_status_handler
        )
        self._build_orchestrate_decomposition_summary_handler = (
            build_orchestrate_decomposition_summary_handler
        )
        self._build_orchestrate_decision_report_handler = (
            build_orchestrate_decision_report_handler
        )
        self._build_orchestrate_telemetry_snapshot_handler = (
            build_orchestrate_telemetry_snapshot_handler
        )
        self._read_orchestrate_latest_record_handler = (
            read_orchestrate_latest_record_handler
        )
        self._persist_orchestrate_latest_record_handler = (
            persist_orchestrate_latest_record_handler
        )
        self._resolve_orchestrate_recovery_action_handler = (
            resolve_orchestrate_recovery_action_handler
        )
        self._get_pending_decomposition_handler = get_pending_decomposition_handler
        self._get_pending_confirmation_status_handler = (
            get_pending_confirmation_status_handler
        )
        self._decompose_bootstrap_workflow_run_handler = (
            decompose_bootstrap_workflow_run_handler
        )
        self._execute_workflow_run_handler = execute_workflow_run_handler
        self._get_decompose_bootstrap_preview_handler = (
            get_decompose_bootstrap_preview_handler
        )
        self._confirm_decompose_bootstrap_workflow_run_handler = (
            confirm_decompose_bootstrap_workflow_run_handler
        )
        self._advance_decompose_bootstrap_run_loop_handler = (
            advance_decompose_bootstrap_run_loop_handler
        )

    async def orchestrate_workflow_run(
        self,
        run_id: str,
        payload: WorkflowRunOrchestrateRequest,
    ) -> WorkflowRunOrchestrateResponse:
        started_at = self._now_utc_handler()
        scheduler = self._workflow_scheduler_provider()
        try:
            run = scheduler.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        status_before = self._build_decompose_aggregate_status_handler(run_id, run)
        strategy = payload.strategy
        execution_profile = derive_execution_profile(
            payload=payload,
            status_before=status_before,
        )

        decompose_payload = resolve_decompose_payload(payload)

        actions: list[str] = []
        orchestration_status = "noop"
        reason: str | None = None
        decompose_result: DecomposeBootstrapWorkflowResponse | None = None
        execute_result: ExecuteWorkflowRunResponse | None = None

        try:
            if run.status == WorkflowRunStatus.CANCELED:
                orchestration_status = "blocked"
                reason = "workflow run is canceled; restart workflow run before orchestrate"
            else:
                should_redecompose = payload.force_redecompose
                should_decompose_when_empty = (
                    (not status_before.has_decomposition) and status_before.workitem_total == 0
                )
                should_decompose = should_redecompose or should_decompose_when_empty
                if should_redecompose and status_before.workitem_total > 0:
                    orchestration_status = "blocked"
                    reason = "force_redecompose is not allowed when workitems already exist"
                elif should_decompose:
                    if decompose_payload is None:
                        orchestration_status = "blocked"
                        reason = (
                            "decompose_payload.requirements (or requirements) is required when decomposition is missing "
                            "or force_redecompose=true"
                        )
                    else:
                        decompose_result = await self._decompose_bootstrap_workflow_run_handler(
                            run_id,
                            DecomposeBootstrapWorkflowRequest(
                                requirements=decompose_payload.requirements,
                                max_modules=decompose_payload.max_modules,
                                module_hints=decompose_payload.module_hints,
                                requested_by=decompose_payload.requested_by,
                            ),
                        )
                        actions.append("decompose_bootstrap")

                if orchestration_status != "blocked" and payload.execute:
                    actions.append("execute_workflow_run")
                    execute_result = await self._execute_workflow_run_handler(
                        run_id,
                        build_orchestrate_execute_request(
                            payload=payload,
                            profile=execution_profile,
                        ),
                    )
        except HTTPException as exc:
            if exc.status_code in {409, 422}:
                orchestration_status = "blocked"
                reason = str(exc.detail)
            else:
                raise
        except ValueError as exc:
            orchestration_status = "blocked"
            reason = str(exc)

        if orchestration_status != "blocked":
            if execute_result is not None:
                orchestration_status = "executed"
            elif decompose_result is not None:
                orchestration_status = "prepared"
            else:
                orchestration_status = "noop"

        run_after = scheduler.get_run(run_id)
        status_after = self._build_decompose_aggregate_status_handler(run_id, run_after)
        decomposition_summary = self._build_orchestrate_decomposition_summary_handler(
            run_after,
            status_after,
        )
        decision_report = self._build_orchestrate_decision_report_handler(
            run_id,
            strategy,
            execution_profile,
            orchestration_status,
            reason,
            actions,
            status_before,
            status_after,
        )
        telemetry_snapshot = self._build_orchestrate_telemetry_snapshot_handler(
            started_at,
            self._now_utc_handler(),
            actions,
            status_before,
            status_after,
            execute_result,
        )
        self._persist_orchestrate_latest_record_handler(
            run_id,
            run_after,
            strategy,
            orchestration_status,
            reason,
            actions,
            decision_report,
            telemetry_snapshot,
        )
        return WorkflowRunOrchestrateResponse(
            run_id=run_id,
            strategy=strategy,
            orchestration_status=orchestration_status,
            reason=reason,
            actions=actions,
            status_before=status_before,
            status_after=status_after,
            decomposition_summary=decomposition_summary,
            decision_report=decision_report,
            telemetry_snapshot=telemetry_snapshot,
            decompose=decompose_result,
            execute=execute_result,
        )

    async def get_latest_orchestrate_telemetry(
        self,
        run_id: str,
    ) -> WorkflowRunOrchestrateLatestTelemetryResponse:
        scheduler = self._workflow_scheduler_provider()
        try:
            run = scheduler.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        record = self._read_orchestrate_latest_record_handler(run)
        return WorkflowRunOrchestrateLatestTelemetryResponse(
            run_id=run_id,
            found=record is not None,
            record=record,
        )

    async def execute_orchestrate_recovery_action(
        self,
        run_id: str,
        payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
    ) -> WorkflowRunOrchestrateRecoveryExecuteResponse:
        scheduler = self._workflow_scheduler_provider()
        try:
            run = scheduler.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        latest_record = self._read_orchestrate_latest_record_handler(run)
        selected_action, action_source = self._resolve_orchestrate_recovery_action_handler(
            payload,
            latest_record,
        )
        if not selected_action:
            return build_recovery_response(
                run_id=run_id,
                action_source=action_source,
                selected_action=None,
                action_status="blocked",
                reason="no recovery action in request or latest decision report",
                restarted_run_id=None,
                restarted_run_status=None,
                latest_record_before=latest_record,
                orchestrate=None,
                preview=None,
                confirmation=None,
                advance_loop=None,
                execute=None,
            )

        orchestrate_result: WorkflowRunOrchestrateResponse | None = None
        preview_result: DecomposeBootstrapPreviewResponse | None = None
        confirmation_result: ConfirmDecomposeBootstrapWorkflowResponse | None = None
        advance_loop_result: DecomposeBootstrapAdvanceLoopResponse | None = None
        execute_result: ExecuteWorkflowRunResponse | None = None
        restarted_run_id: str | None = None
        restarted_run_status: str | None = None

        try:
            if selected_action in {"generate_preview", "refresh_preview"}:
                preview_result = await self._get_decompose_bootstrap_preview_handler(
                    run_id,
                    (
                        selected_action == "refresh_preview"
                        or payload.auto_advance_force_refresh_preview
                    ),
                )
            elif selected_action in {
                "reconfirm_decomposition",
                "reconfirm_with_latest_token",
            }:
                pending = self._get_pending_decomposition_handler(run)
                if pending is None:
                    raise HTTPException(status_code=409, detail="no pending decomposition to confirm")
                if self._get_pending_confirmation_status_handler(pending) != "pending":
                    raise HTTPException(
                        status_code=409,
                        detail="decomposition confirmation is not pending",
                    )
                confirmed_by = self._optional_text_handler(payload.confirmed_by)
                if not confirmed_by:
                    raise HTTPException(
                        status_code=422,
                        detail="confirmed_by is required for decomposition confirmation",
                    )
                confirmation_token = self._optional_text_handler(payload.confirmation_token)
                if selected_action == "reconfirm_with_latest_token" and not confirmation_token:
                    confirmation_token = resolve_latest_confirmation_token(
                        pending=pending,
                        optional_text_handler=self._optional_text_handler,
                    )
                confirmation_result = await self._confirm_decompose_bootstrap_workflow_run_handler(
                    run_id,
                    ConfirmDecomposeBootstrapWorkflowRequest(
                        approved=True,
                        confirmed_by=confirmed_by,
                        reason=f"orchestrate recovery action: {selected_action}",
                        confirmation_token=confirmation_token,
                        expected_modules=payload.expected_modules,
                    ),
                )
            elif selected_action == "retry_bootstrap_pipeline":
                advance_loop_result = await self._advance_decompose_bootstrap_run_loop_handler(
                    run_id,
                    build_recovery_advance_loop_request(
                        payload,
                    ),
                )
            elif selected_action in {
                "retry_execute_workflow_run",
                "wait_or_unblock_workitems",
            }:
                execute_result = await self._execute_workflow_run_handler(
                    run_id,
                    build_recovery_execute_request(
                        payload,
                    ),
                )
            elif selected_action in {
                "retry_with_decompose_payload",
                "disable_force_redecompose",
                "retry_orchestrate",
            }:
                requirements = self._optional_text_handler(payload.requirements)
                if selected_action == "retry_with_decompose_payload" and not requirements:
                    raise HTTPException(
                        status_code=422,
                        detail="requirements is required for retry_with_decompose_payload",
                    )
                decompose_payload: WorkflowRunOrchestrateDecomposePayload | None = None
                if requirements:
                    decompose_payload = WorkflowRunOrchestrateDecomposePayload(
                        requirements=requirements,
                        module_hints=payload.module_hints,
                        max_modules=payload.max_modules,
                        requested_by=payload.requested_by,
                    )

                orchestrate_result = await self.orchestrate_workflow_run(
                    run_id,
                    build_recovery_orchestrate_request(
                        payload=payload,
                        requirements=requirements,
                        decompose_payload=decompose_payload,
                    ),
                )
            elif selected_action == "restart_workflow_run":
                restarted_run, _ = scheduler.restart_run(
                    run_id=run_id,
                    requested_by=payload.requested_by,
                    reason=f"orchestrate recovery action: {selected_action}",
                    copy_decomposition=True,
                )
                restarted_run_id = restarted_run.id
                restarted_run_status = restarted_run.status.value
            else:
                raise HTTPException(
                    status_code=422,
                    detail=f"unsupported recovery action: {selected_action}",
                )

            return build_recovery_response(
                run_id=run_id,
                action_source=action_source,
                selected_action=selected_action,
                action_status="executed",
                reason=None,
                restarted_run_id=restarted_run_id,
                restarted_run_status=restarted_run_status,
                latest_record_before=latest_record,
                orchestrate=orchestrate_result,
                preview=preview_result,
                confirmation=confirmation_result,
                advance_loop=advance_loop_result,
                execute=execute_result,
            )
        except HTTPException as exc:
            if exc.status_code in {409, 422}:
                return build_recovery_response(
                    run_id=run_id,
                    action_source=action_source,
                    selected_action=selected_action,
                    action_status="blocked",
                    reason=str(exc.detail),
                    restarted_run_id=restarted_run_id,
                    restarted_run_status=restarted_run_status,
                    latest_record_before=latest_record,
                    orchestrate=orchestrate_result,
                    preview=preview_result,
                    confirmation=confirmation_result,
                    advance_loop=advance_loop_result,
                    execute=execute_result,
                )
            raise
        except ValueError as exc:
            return build_recovery_response(
                run_id=run_id,
                action_source=action_source,
                selected_action=selected_action,
                action_status="blocked",
                reason=str(exc),
                restarted_run_id=restarted_run_id,
                restarted_run_status=restarted_run_status,
                latest_record_before=latest_record,
                orchestrate=orchestrate_result,
                preview=preview_result,
                confirmation=confirmation_result,
                advance_loop=advance_loop_result,
                execute=execute_result,
            )
