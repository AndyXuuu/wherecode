from __future__ import annotations

from collections.abc import Callable

from control_center.models import (
    Artifact,
    DecomposeBootstrapAggregateStatusResponse,
    WorkflowRun,
    WorkflowRunRoutingDecision,
    WorkflowRunRoutingDecisionsResponse,
    WorkItem,
)


class WorkflowDecomposeSupportService:
    def __init__(
        self,
        *,
        select_decomposition_for_preview_handler: Callable[
            [WorkflowRun], tuple[dict[str, object] | None, str]
        ],
        extract_preview_modules_handler: Callable[[dict[str, object]], list[str]],
        get_preview_snapshot_status_handler: Callable[
            [WorkflowRun, dict[str, object]],
            tuple[bool, bool, str | None, str | None],
        ],
        get_pending_decomposition_handler: Callable[[WorkflowRun], dict[str, object] | None],
        optional_text_handler: Callable[[object], str | None],
        normalize_text_list_handler: Callable[[object], list[str]],
        list_workitems_handler: Callable[[str], list[WorkItem]],
        list_artifacts_handler: Callable[[str], list[Artifact]],
    ) -> None:
        self._select_decomposition_for_preview_handler = (
            select_decomposition_for_preview_handler
        )
        self._extract_preview_modules_handler = extract_preview_modules_handler
        self._get_preview_snapshot_status_handler = (
            get_preview_snapshot_status_handler
        )
        self._get_pending_decomposition_handler = get_pending_decomposition_handler
        self._optional_text_handler = optional_text_handler
        self._normalize_text_list_handler = normalize_text_list_handler
        self._list_workitems_handler = list_workitems_handler
        self._list_artifacts_handler = list_artifacts_handler

    @staticmethod
    def _build_workitem_status_counts(workitems: list[WorkItem]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in workitems:
            status_value = (
                item.status.value
                if hasattr(item.status, "value")
                else str(item.status).strip().lower()
            )
            counts[status_value] = counts.get(status_value, 0) + 1
        return {key: counts[key] for key in sorted(counts.keys())}

    @staticmethod
    def _build_module_workitem_counts(
        workitems: list[WorkItem],
    ) -> tuple[dict[str, int], int]:
        module_counts: dict[str, int] = {}
        global_count = 0
        for item in workitems:
            module_key = str(item.module_key or "").strip() or "global"
            if module_key == "global":
                global_count += 1
                continue
            module_counts[module_key] = module_counts.get(module_key, 0) + 1
        return ({key: module_counts[key] for key in sorted(module_counts.keys())}, global_count)

    @staticmethod
    def _build_decompose_next_action(
        *,
        has_decomposition: bool,
        has_pending_confirmation: bool,
        preview_ready: bool,
        preview_stale: bool,
        workitem_total: int,
        workitem_status_counts: dict[str, int],
        acceptance_evidence_complete: bool,
    ) -> str:
        if workitem_total > 0:
            ready_count = workitem_status_counts.get("ready", 0)
            if ready_count > 0:
                return "execute_workflow_run"

            unfinished_count = (
                workitem_status_counts.get("pending", 0)
                + workitem_status_counts.get("running", 0)
                + workitem_status_counts.get("waiting_approval", 0)
                + workitem_status_counts.get("needs_discussion", 0)
            )
            if unfinished_count > 0:
                return "wait_or_unblock_workitems"
            if acceptance_evidence_complete:
                return "accepted"
            return "complete_acceptance_evidence"

        if not has_decomposition:
            return "trigger_decompose_bootstrap"
        if has_pending_confirmation:
            return "confirm_or_reject_decomposition"
        if preview_stale:
            return "refresh_preview"
        if not preview_ready:
            return "generate_preview"
        return "bootstrap_pipeline"

    def build_decompose_aggregate_status(
        self,
        run_id: str,
        run: WorkflowRun,
    ) -> DecomposeBootstrapAggregateStatusResponse:
        decomposition, source = self._select_decomposition_for_preview_handler(run)
        has_decomposition = decomposition is not None
        modules: list[str] = []
        preview_ready = False
        preview_stale = False
        preview_generated_at: str | None = None
        preview_fingerprint: str | None = None
        if decomposition is not None:
            modules = self._extract_preview_modules_handler(decomposition)
            (
                preview_ready,
                preview_stale,
                preview_generated_at,
                preview_fingerprint,
            ) = self._get_preview_snapshot_status_handler(run, decomposition)

        pending = self._get_pending_decomposition_handler(run)
        confirmation_status: str | None = None
        has_pending_confirmation = False
        if pending is not None:
            confirmation = pending.get("confirmation")
            if isinstance(confirmation, dict):
                confirmation_status = self._optional_text_handler(
                    confirmation.get("status")
                )
                has_pending_confirmation = confirmation_status == "pending"
        elif isinstance(run.metadata.get("chief_decomposition"), dict):
            chief_confirmation = run.metadata["chief_decomposition"].get("confirmation")
            if isinstance(chief_confirmation, dict):
                confirmation_status = self._optional_text_handler(
                    chief_confirmation.get("status")
                )

        workitems = self._list_workitems_handler(run_id)
        workitem_status_counts = self._build_workitem_status_counts(workitems)
        module_workitem_counts, global_workitem_count = self._build_module_workitem_counts(
            workitems
        )
        workitem_total = len(workitems)
        artifacts = self._list_artifacts_handler(run_id)
        artifact_types = {artifact.artifact_type.value for artifact in artifacts}
        acceptance_evidence_complete = {
            "acceptance_report",
            "release_note",
            "rollback_plan",
        }.issubset(artifact_types)
        unfinished_count = (
            workitem_status_counts.get("pending", 0)
            + workitem_status_counts.get("ready", 0)
            + workitem_status_counts.get("running", 0)
            + workitem_status_counts.get("waiting_approval", 0)
            + workitem_status_counts.get("needs_discussion", 0)
        )
        bootstrap_started = workitem_total > 0
        bootstrap_finished = bootstrap_started and unfinished_count == 0
        next_action = self._build_decompose_next_action(
            has_decomposition=has_decomposition,
            has_pending_confirmation=has_pending_confirmation,
            preview_ready=preview_ready,
            preview_stale=preview_stale,
            workitem_total=workitem_total,
            workitem_status_counts=workitem_status_counts,
            acceptance_evidence_complete=acceptance_evidence_complete,
        )
        return DecomposeBootstrapAggregateStatusResponse(
            run_id=run_id,
            run_status=run.status,
            requirement_status=run.requirement_status,
            clarification_rounds=run.clarification_rounds,
            assumption_used=run.assumption_used,
            current_stage=run.current_stage,
            next_action_hint=run.next_action_hint,
            blocked_reason=run.blocked_reason,
            accepted=run.accepted,
            acceptance_evidence_complete=acceptance_evidence_complete,
            decomposition_source=source,
            has_decomposition=has_decomposition,
            has_pending_confirmation=has_pending_confirmation,
            confirmation_status=confirmation_status,
            modules=modules,
            preview_ready=preview_ready,
            preview_stale=preview_stale,
            preview_generated_at=preview_generated_at,
            preview_fingerprint=preview_fingerprint,
            workitem_total=workitem_total,
            workitem_status_counts=workitem_status_counts,
            module_workitem_counts=module_workitem_counts,
            global_workitem_count=global_workitem_count,
            bootstrap_started=bootstrap_started,
            bootstrap_finished=bootstrap_finished,
            next_action=next_action,
        )

    def build_routing_decisions_response(
        self,
        run_id: str,
        run: WorkflowRun,
    ) -> WorkflowRunRoutingDecisionsResponse:
        decomposition, source = self._select_decomposition_for_preview_handler(run)
        if decomposition is None:
            return WorkflowRunRoutingDecisionsResponse(
                run_id=run_id,
                source=source,
                confirmation_status=None,
                has_routing_decisions=False,
                module_count=0,
                decisions=[],
            )

        confirmation_status: str | None = None
        confirmation = decomposition.get("confirmation")
        if isinstance(confirmation, dict):
            confirmation_status = self._optional_text_handler(confirmation.get("status"))

        raw_decisions = decomposition.get("module_routing_decisions")
        routing_map = raw_decisions if isinstance(raw_decisions, dict) else {}
        modules = self._extract_preview_modules_handler(decomposition)
        module_keys: list[str] = []
        for module in modules:
            if module not in module_keys:
                module_keys.append(module)
        for module in routing_map.keys():
            normalized_module = str(module).strip()
            if normalized_module and normalized_module not in module_keys:
                module_keys.append(normalized_module)

        decisions: list[WorkflowRunRoutingDecision] = []
        for module_key in module_keys:
            raw_entry = routing_map.get(module_key)
            entry = raw_entry if isinstance(raw_entry, dict) else {}
            target_raw = entry.get("target")
            target = target_raw if isinstance(target_raw, dict) else {}

            signals_raw = entry.get("signals")
            signals: dict[str, list[str]] = {}
            if isinstance(signals_raw, dict):
                for key, value in signals_raw.items():
                    normalized_values = self._normalize_text_list_handler(value)
                    if normalized_values:
                        signals[str(key)] = normalized_values

            decisions.append(
                WorkflowRunRoutingDecision(
                    module_key=module_key,
                    rule_id=self._optional_text_handler(entry.get("rule_id")),
                    target_role=self._optional_text_handler(target.get("role")),
                    capability_id=self._optional_text_handler(target.get("capability_id")),
                    executor=self._optional_text_handler(target.get("executor")),
                    required_checks=self._normalize_text_list_handler(
                        entry.get("required_checks")
                    ),
                    handoff_roles=self._normalize_text_list_handler(
                        entry.get("handoff_roles")
                    ),
                    requires_human_confirmation=bool(
                        entry.get("requires_human_confirmation", False)
                    ),
                    signals=signals,
                )
            )

        return WorkflowRunRoutingDecisionsResponse(
            run_id=run_id,
            source=source,
            confirmation_status=confirmation_status,
            has_routing_decisions=bool(decisions),
            module_count=len(module_keys),
            decisions=decisions,
        )
