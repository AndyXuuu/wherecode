from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException

from control_center.models import (
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    ExecuteWorkflowRunRequest,
    ExecuteWorkflowRunResponse,
    InterruptWorkflowRunRequest,
    InterruptWorkflowRunResponse,
    WorkflowRun,
)
from control_center.services.workflow_engine import WorkflowEngine
from control_center.services.workflow_scheduler import WorkflowScheduler


class WorkflowExecutionRuntimeService:
    def __init__(
        self,
        *,
        workflow_scheduler_provider: Callable[[], WorkflowScheduler],
        workflow_engine_provider: Callable[[], WorkflowEngine],
        advance_decompose_bootstrap_run_loop_handler: Callable[
            [str, DecomposeBootstrapAdvanceLoopRequest],
            Awaitable[DecomposeBootstrapAdvanceLoopResponse],
        ],
        get_pending_decomposition: Callable[[WorkflowRun], dict[str, object] | None],
        get_pending_confirmation_status: Callable[[dict[str, object]], str],
    ) -> None:
        self._workflow_scheduler_provider = workflow_scheduler_provider
        self._workflow_engine_provider = workflow_engine_provider
        self._advance_decompose_bootstrap_run_loop_handler = (
            advance_decompose_bootstrap_run_loop_handler
        )
        self._get_pending_decomposition = get_pending_decomposition
        self._get_pending_confirmation_status = get_pending_confirmation_status

    async def execute_workflow_run(
        self,
        run_id: str,
        payload: ExecuteWorkflowRunRequest,
    ) -> ExecuteWorkflowRunResponse:
        auto_advance_result: DecomposeBootstrapAdvanceLoopResponse | None = None
        if payload.auto_advance_decompose:
            try:
                auto_advance_result = await self._advance_decompose_bootstrap_run_loop_handler(
                    run_id,
                    DecomposeBootstrapAdvanceLoopRequest(
                        confirmed_by=payload.decompose_confirmed_by,
                        confirmation_token=payload.decompose_confirmation_token,
                        expected_modules=payload.decompose_expected_modules,
                        execute_max_loops=(
                            payload.auto_advance_execute_max_loops
                            if payload.auto_advance_execute_max_loops is not None
                            else payload.max_loops
                        ),
                        force_refresh_preview=payload.auto_advance_force_refresh_preview,
                        max_steps=payload.auto_advance_max_steps,
                        stop_when_bootstrap_finished=False,
                    ),
                )
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

        scheduler = self._workflow_scheduler_provider()
        try:
            run = scheduler.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        pending = self._get_pending_decomposition(run)
        if pending is not None and self._get_pending_confirmation_status(pending) == "pending":
            detail = "decomposition confirmation required before execute"
            if auto_advance_result is not None and auto_advance_result.steps:
                last_step = auto_advance_result.steps[-1]
                if last_step.reason:
                    detail = f"{detail}: {last_step.reason}"
            raise HTTPException(status_code=409, detail=detail)

        try:
            execution_result = await self._workflow_engine_provider().execute_until_blocked(
                run_id=run_id,
                max_loops=payload.max_loops,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if auto_advance_result is None:
            return execution_result
        return self._merge_auto_advance_execution_result(
            execution_result=execution_result,
            auto_advance_result=auto_advance_result,
        )

    async def interrupt_workflow_run(
        self,
        run_id: str,
        payload: InterruptWorkflowRunRequest,
    ) -> InterruptWorkflowRunResponse:
        scheduler = self._workflow_scheduler_provider()
        try:
            (
                previous_status,
                run_status,
                interrupt_applied,
                skipped_workitem_ids,
            ) = scheduler.interrupt_run(
                run_id=run_id,
                requested_by=payload.requested_by,
                reason=payload.reason,
                skip_non_terminal_workitems=payload.skip_non_terminal_workitems,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return InterruptWorkflowRunResponse(
            run_id=run_id,
            previous_status=previous_status,
            run_status=run_status,
            interrupt_applied=interrupt_applied,
            skipped_workitem_ids=skipped_workitem_ids,
            reason=payload.reason,
        )

    @staticmethod
    def _merge_auto_advance_execution_result(
        *,
        execution_result: ExecuteWorkflowRunResponse,
        auto_advance_result: DecomposeBootstrapAdvanceLoopResponse,
    ) -> ExecuteWorkflowRunResponse:
        updated_fields: dict[str, object] = {
            "decompose_auto_advance": auto_advance_result,
        }
        if execution_result.executed_count == 0 and execution_result.failed_count == 0:
            auto_exec_results = [
                step.execute
                for step in auto_advance_result.steps
                if step.execute is not None
            ]
            if auto_exec_results:
                auto_executed_ids: list[str] = []
                auto_failed_ids: list[str] = []
                for result in auto_exec_results:
                    for workitem_id in result.executed_workitem_ids:
                        if workitem_id not in auto_executed_ids:
                            auto_executed_ids.append(workitem_id)
                    for workitem_id in result.failed_workitem_ids:
                        if workitem_id not in auto_failed_ids:
                            auto_failed_ids.append(workitem_id)
                if auto_executed_ids:
                    updated_fields["executed_workitem_ids"] = auto_executed_ids
                    updated_fields["executed_count"] = len(auto_executed_ids)
                else:
                    updated_fields["executed_count"] = max(
                        result.executed_count for result in auto_exec_results
                    )
                if auto_failed_ids:
                    updated_fields["failed_workitem_ids"] = auto_failed_ids
                    updated_fields["failed_count"] = len(auto_failed_ids)
                else:
                    updated_fields["failed_count"] = max(
                        result.failed_count for result in auto_exec_results
                    )
        return execution_result.model_copy(update=updated_fields)
