from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException

from control_center.models import (
    ArtifactType,
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    ExecuteWorkflowRunRequest,
    ExecuteWorkflowRunResponse,
    InterruptWorkflowRunRequest,
    InterruptWorkflowRunResponse,
    RequirementStatus,
    SDDStage,
    WorkflowRun,
    WorkflowRunStatus,
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

        if run.requirement_status != RequirementStatus.CONFIRMED:
            run.blocked_reason = "requirement_not_confirmed"
            run.next_action_hint = "awaiting_clarification"
            scheduler.persist_run(run.id)
            raise HTTPException(
                status_code=409,
                detail=(
                    "requirement is not confirmed; "
                    "clarification is required before implement stage"
                ),
            )

        missing_stages = self._missing_pre_implement_stages(run)
        if missing_stages:
            run.requirement_status = RequirementStatus.BLOCKED
            run.blocked_reason = f"missing_sdd_artifacts:{','.join(missing_stages)}"
            run.next_action_hint = "provide_missing_sdd_artifacts"
            scheduler.persist_run(run.id)
            raise HTTPException(
                status_code=409,
                detail=f"missing required SDD artifacts before implement: {', '.join(missing_stages)}",
            )
        run.current_stage = SDDStage.IMPLEMENT
        run.next_action_hint = "execute_workflow_run"
        run.blocked_reason = None
        scheduler.persist_run(run.id)

        try:
            execution_result = await self._workflow_engine_provider().execute_until_blocked(
                run_id=run_id,
                max_loops=payload.max_loops,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        merged_result = (
            execution_result
            if auto_advance_result is None
            else self._merge_auto_advance_execution_result(
                execution_result=execution_result,
                auto_advance_result=auto_advance_result,
            )
        )
        self._update_stage_and_acceptance_after_execute(scheduler, run_id)
        return merged_result

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
    def _missing_pre_implement_stages(run: WorkflowRun) -> list[str]:
        stage_artifacts = run.metadata.get("sdd_stage_artifacts")
        if not isinstance(stage_artifacts, dict):
            return ["intent", "spec", "design", "tasks"]
        missing: list[str] = []
        for stage in ("intent", "spec", "design", "tasks"):
            artifact_id = stage_artifacts.get(stage)
            if not isinstance(artifact_id, str) or not artifact_id.strip():
                missing.append(stage)
        return missing

    @staticmethod
    def _has_acceptance_evidence(scheduler: WorkflowScheduler, run_id: str) -> bool:
        artifacts = scheduler.list_artifacts(run_id)
        artifact_types = {artifact.artifact_type for artifact in artifacts}
        required = {
            ArtifactType.ACCEPTANCE_REPORT,
            ArtifactType.RELEASE_NOTE,
            ArtifactType.ROLLBACK_PLAN,
        }
        return required.issubset(artifact_types)

    @classmethod
    def _update_stage_and_acceptance_after_execute(
        cls,
        scheduler: WorkflowScheduler,
        run_id: str,
    ) -> None:
        run = scheduler.get_run(run_id)
        evidence_complete = cls._has_acceptance_evidence(scheduler, run_id)
        run.metadata["acceptance_evidence_complete"] = evidence_complete
        if run.status == WorkflowRunStatus.SUCCEEDED and evidence_complete:
            run.current_stage = SDDStage.ACCEPT
            run.accepted = True
            run.next_action_hint = "none"
            run.blocked_reason = None
            run.requirement_status = RequirementStatus.CONFIRMED
        elif run.status == WorkflowRunStatus.SUCCEEDED and not evidence_complete:
            run.status = WorkflowRunStatus.BLOCKED
            run.current_stage = SDDStage.VERIFY
            run.accepted = False
            run.blocked_reason = "acceptance_evidence_incomplete"
            run.next_action_hint = "complete_acceptance_evidence"
            run.requirement_status = RequirementStatus.BLOCKED
        else:
            run.current_stage = SDDStage.IMPLEMENT
            run.accepted = False
            if run.status == WorkflowRunStatus.BLOCKED:
                run.next_action_hint = "resolve_workitem_blocks"
            elif run.status == WorkflowRunStatus.FAILED:
                run.next_action_hint = "repair_failed_workitems"
            elif run.status == WorkflowRunStatus.WAITING_APPROVAL:
                run.next_action_hint = "approve_waiting_workitems"
        scheduler.persist_run(run.id)

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
