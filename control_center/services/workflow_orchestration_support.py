from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from control_center.models import (
    DecomposeBootstrapAggregateStatusResponse,
    ExecuteWorkflowRunResponse,
    WorkflowRun,
    WorkflowRunOrchestrateDecisionReport,
    WorkflowRunOrchestrateDecompositionSummary,
    WorkflowRunOrchestrateExecutionProfile,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateStrategy,
    WorkflowRunOrchestrateTelemetryRecord,
    WorkflowRunOrchestrateTelemetrySnapshot,
)
from control_center.services.workflow_orchestration_support_decision import (
    build_orchestrate_decision_report_impl,
)
from control_center.services.workflow_orchestration_support_summary import (
    build_orchestrate_decomposition_summary_impl,
    build_orchestrate_telemetry_snapshot_impl,
    count_unfinished_workitems_from_aggregate_status,
    resolve_orchestrate_recovery_action_impl,
)


class WorkflowOrchestrationSupportService:
    def __init__(
        self,
        *,
        select_decomposition_for_preview_handler: Callable[
            [WorkflowRun], tuple[dict[str, object] | None, str]
        ],
        extract_preview_modules_handler: Callable[[dict[str, object]], list[str]],
        get_pending_decomposition_handler: Callable[[WorkflowRun], dict[str, object] | None],
        optional_text_handler: Callable[[object], str | None],
        now_utc_handler: Callable[[], datetime],
        persist_run_handler: Callable[[str], object],
    ) -> None:
        self._select_decomposition_for_preview_handler = (
            select_decomposition_for_preview_handler
        )
        self._extract_preview_modules_handler = extract_preview_modules_handler
        self._get_pending_decomposition_handler = get_pending_decomposition_handler
        self._optional_text_handler = optional_text_handler
        self._now_utc_handler = now_utc_handler
        self._persist_run_handler = persist_run_handler

    def build_orchestrate_decomposition_summary(
        self,
        run: WorkflowRun,
        aggregate_status: DecomposeBootstrapAggregateStatusResponse,
    ) -> WorkflowRunOrchestrateDecompositionSummary | None:
        return build_orchestrate_decomposition_summary_impl(
            run=run,
            aggregate_status=aggregate_status,
            select_decomposition_for_preview_handler=(
                self._select_decomposition_for_preview_handler
            ),
            extract_preview_modules_handler=self._extract_preview_modules_handler,
            get_pending_decomposition_handler=self._get_pending_decomposition_handler,
            optional_text_handler=self._optional_text_handler,
        )

    def build_orchestrate_decision_report(
        self,
        run_id: str,
        strategy: WorkflowRunOrchestrateStrategy,
        execution_profile: WorkflowRunOrchestrateExecutionProfile,
        orchestration_status: str,
        reason: str | None,
        actions: list[str],
        status_before: DecomposeBootstrapAggregateStatusResponse,
        status_after: DecomposeBootstrapAggregateStatusResponse,
    ) -> WorkflowRunOrchestrateDecisionReport:
        return build_orchestrate_decision_report_impl(
            run_id=run_id,
            strategy=strategy,
            execution_profile=execution_profile,
            orchestration_status=orchestration_status,
            reason=reason,
            actions=actions,
            status_before=status_before,
            status_after=status_after,
        )

    @staticmethod
    def _count_unfinished_workitems_from_aggregate_status(
        status: DecomposeBootstrapAggregateStatusResponse,
    ) -> int:
        return count_unfinished_workitems_from_aggregate_status(status)

    def build_orchestrate_telemetry_snapshot(
        self,
        started_at: datetime,
        finished_at: datetime,
        actions: list[str],
        status_before: DecomposeBootstrapAggregateStatusResponse,
        status_after: DecomposeBootstrapAggregateStatusResponse,
        execute_result: ExecuteWorkflowRunResponse | None,
    ) -> WorkflowRunOrchestrateTelemetrySnapshot:
        return build_orchestrate_telemetry_snapshot_impl(
            started_at=started_at,
            finished_at=finished_at,
            actions=actions,
            status_before=status_before,
            status_after=status_after,
            execute_result=execute_result,
        )

    @staticmethod
    def read_orchestrate_latest_record(
        run: WorkflowRun,
    ) -> WorkflowRunOrchestrateTelemetryRecord | None:
        raw_value = run.metadata.get("orchestrate_telemetry_latest")
        if not isinstance(raw_value, dict):
            return None
        try:
            return WorkflowRunOrchestrateTelemetryRecord.model_validate(raw_value)
        except Exception:
            return None

    def persist_orchestrate_latest_record(
        self,
        run_id: str,
        run: WorkflowRun,
        strategy: WorkflowRunOrchestrateStrategy,
        orchestration_status: str,
        reason: str | None,
        actions: list[str],
        decision_report: WorkflowRunOrchestrateDecisionReport | None,
        telemetry_snapshot: WorkflowRunOrchestrateTelemetrySnapshot,
    ) -> WorkflowRunOrchestrateTelemetryRecord:
        record = WorkflowRunOrchestrateTelemetryRecord(
            run_id=run_id,
            strategy=strategy,
            orchestration_status=orchestration_status,
            reason=reason,
            actions=actions,
            decision_report=decision_report,
            telemetry_snapshot=telemetry_snapshot,
            recorded_at=self._now_utc_handler(),
        )
        run.metadata["orchestrate_telemetry_latest"] = record.model_dump(mode="json")
        self._persist_run_handler(run_id)
        return record

    def resolve_orchestrate_recovery_action(
        self,
        payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
        latest_record: WorkflowRunOrchestrateTelemetryRecord | None,
    ) -> tuple[str | None, str]:
        return resolve_orchestrate_recovery_action_impl(
            payload=payload,
            latest_record=latest_record,
            optional_text_handler=self._optional_text_handler,
        )
