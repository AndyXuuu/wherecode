from __future__ import annotations

from control_center.models import (
    DecomposeBootstrapAggregateStatusResponse,
    WorkflowRunOrchestrateDecisionMachineReport,
    WorkflowRunOrchestrateDecisionReport,
    WorkflowRunOrchestrateExecutionProfile,
    WorkflowRunOrchestrateRecoveryActionScore,
    WorkflowRunOrchestrateStrategy,
)


def build_orchestrate_decision_report_impl(
    *,
    run_id: str,
    strategy: WorkflowRunOrchestrateStrategy,
    execution_profile: WorkflowRunOrchestrateExecutionProfile,
    orchestration_status: str,
    reason: str | None,
    actions: list[str],
    status_before: DecomposeBootstrapAggregateStatusResponse,
    status_after: DecomposeBootstrapAggregateStatusResponse,
) -> WorkflowRunOrchestrateDecisionReport:
    reason_lower = (reason or "").strip().lower()
    strategy_key = strategy.value
    scored_action_map: dict[str, WorkflowRunOrchestrateRecoveryActionScore] = {}

    strategy_score_adjustments: dict[str, dict[str, tuple[int, float]]] = {
        "speed": {
            "retry_with_decompose_payload": (-3, 0.03),
            "retry_bootstrap_pipeline": (-6, 0.08),
            "retry_execute_workflow_run": (-8, 0.1),
            "generate_preview": (-2, 0.02),
            "refresh_preview": (-1, 0.02),
            "reconfirm_decomposition": (6, -0.08),
            "wait_or_unblock_workitems": (8, -0.1),
        },
        "balanced": {
            "retry_with_decompose_payload": (-2, 0.02),
            "retry_bootstrap_pipeline": (-2, 0.04),
            "retry_execute_workflow_run": (-3, 0.05),
            "generate_preview": (-1, 0.01),
            "refresh_preview": (-2, 0.03),
            "reconfirm_decomposition": (1, -0.02),
            "wait_or_unblock_workitems": (2, -0.02),
        },
        "safe": {
            "reconfirm_with_latest_token": (-6, 0.06),
            "reconfirm_decomposition": (-5, 0.06),
            "refresh_preview": (-4, 0.05),
            "wait_or_unblock_workitems": (-2, 0.02),
            "retry_bootstrap_pipeline": (6, -0.06),
            "retry_execute_workflow_run": (10, -0.12),
        },
    }

    def _upsert_recovery_action_score(
        action: str,
        *,
        priority: int,
        confidence: float,
        reason_text: str,
    ) -> None:
        priority_delta, confidence_delta = strategy_score_adjustments.get(
            strategy_key,
            {},
        ).get(action, (0, 0.0))
        adjusted_priority = priority + priority_delta
        if adjusted_priority < 1:
            adjusted_priority = 1
        if adjusted_priority > 100:
            adjusted_priority = 100

        adjusted_confidence = confidence + confidence_delta
        if adjusted_confidence < 0:
            adjusted_confidence = 0.0
        if adjusted_confidence > 1:
            adjusted_confidence = 1.0

        existing = scored_action_map.get(action)
        if existing is None:
            scored_action_map[action] = WorkflowRunOrchestrateRecoveryActionScore(
                action=action,
                priority=adjusted_priority,
                confidence=adjusted_confidence,
                reason=reason_text,
            )
            return
        updated_priority = min(existing.priority, adjusted_priority)
        updated_confidence = max(existing.confidence, adjusted_confidence)
        updated_reason = existing.reason
        if updated_reason != reason_text and reason_text:
            updated_reason = f"{existing.reason}; {reason_text}"
        scored_action_map[action] = WorkflowRunOrchestrateRecoveryActionScore(
            action=action,
            priority=updated_priority,
            confidence=updated_confidence,
            reason=updated_reason,
        )

    if (
        "decompose_payload.requirements" in reason_lower
        or "requirements is required" in reason_lower
        or "decompose-bootstrap request payload is required" in reason_lower
    ):
        _upsert_recovery_action_score(
            "retry_with_decompose_payload",
            priority=10,
            confidence=0.95,
            reason_text="missing decomposition requirements payload",
        )
    if "force_redecompose is not allowed" in reason_lower:
        _upsert_recovery_action_score(
            "disable_force_redecompose",
            priority=15,
            confidence=0.95,
            reason_text="existing workitems forbid force redecompose",
        )
    if "confirmation token mismatch" in reason_lower:
        _upsert_recovery_action_score(
            "reconfirm_with_latest_token",
            priority=8,
            confidence=0.9,
            reason_text="confirmation token mismatch",
        )
    if (
        status_after.run_status.value == "canceled"
        or "workflow run is canceled" in reason_lower
    ):
        _upsert_recovery_action_score(
            "restart_workflow_run",
            priority=5,
            confidence=0.98,
            reason_text="workflow run canceled and requires restart",
        )
    if status_after.has_pending_confirmation:
        _upsert_recovery_action_score(
            "reconfirm_decomposition",
            priority=12,
            confidence=0.9,
            reason_text="decomposition still pending confirmation",
        )
    if status_after.preview_stale:
        _upsert_recovery_action_score(
            "refresh_preview",
            priority=20,
            confidence=0.85,
            reason_text="preview snapshot stale",
        )

    next_action_hint_map: dict[str, tuple[str, int, float, str]] = {
        "generate_preview": (
            "generate_preview",
            30,
            0.8,
            "next action requires preview generation",
        ),
        "refresh_preview": (
            "refresh_preview",
            20,
            0.85,
            "next action requires preview refresh",
        ),
        "confirm_or_reject_decomposition": (
            "reconfirm_decomposition",
            12,
            0.9,
            "next action requires decomposition confirmation",
        ),
        "bootstrap_pipeline": (
            "retry_bootstrap_pipeline",
            25,
            0.75,
            "next action requires bootstrap",
        ),
        "execute_workflow_run": (
            "retry_execute_workflow_run",
            35,
            0.7,
            "next action requires workflow execution",
        ),
        "wait_or_unblock_workitems": (
            "wait_or_unblock_workitems",
            45,
            0.6,
            "workitems are not ready yet",
        ),
        "trigger_decompose_bootstrap": (
            "retry_with_decompose_payload",
            10,
            0.95,
            "decompose bootstrap missing",
        ),
    }
    mapped_next_action = next_action_hint_map.get(status_after.next_action or "")
    if mapped_next_action:
        (
            next_action,
            next_priority,
            next_confidence,
            next_reason,
        ) = mapped_next_action
        _upsert_recovery_action_score(
            next_action,
            priority=next_priority,
            confidence=next_confidence,
            reason_text=next_reason,
        )

    if orchestration_status == "blocked" and not scored_action_map:
        _upsert_recovery_action_score(
            "retry_orchestrate",
            priority=60,
            confidence=0.5,
            reason_text="generic blocked fallback",
        )

    scored_recovery_actions = sorted(
        scored_action_map.values(),
        key=lambda item: (item.priority, -item.confidence, item.action),
    )
    recovery_actions = [item.action for item in scored_recovery_actions]
    primary_recovery_action = recovery_actions[0] if recovery_actions else None
    primary_recovery_priority = (
        scored_recovery_actions[0].priority if scored_recovery_actions else None
    )
    primary_recovery_confidence = (
        scored_recovery_actions[0].confidence if scored_recovery_actions else None
    )

    machine = WorkflowRunOrchestrateDecisionMachineReport(
        run_id=run_id,
        strategy=strategy,
        orchestration_status=orchestration_status,
        reason=reason,
        actions=actions,
        next_action_before=status_before.next_action,
        next_action_after=status_after.next_action,
        decompose_triggered=("decompose_bootstrap" in actions),
        execute_triggered=("execute_workflow_run" in actions),
        pending_confirmation_before=status_before.has_pending_confirmation,
        pending_confirmation_after=status_after.has_pending_confirmation,
        preview_ready_after=status_after.preview_ready,
        workitem_total_after=status_after.workitem_total,
        primary_recovery_action=primary_recovery_action,
        recovery_actions=recovery_actions,
        primary_recovery_priority=primary_recovery_priority,
        primary_recovery_confidence=primary_recovery_confidence,
        scored_recovery_actions=scored_recovery_actions,
        execution_profile=execution_profile,
    )
    action_text = ",".join(actions) if actions else "none"
    reason_text = reason if reason else "none"
    recovery_text = ",".join(recovery_actions) if recovery_actions else "none"
    primary_recovery_text = (
        f"{primary_recovery_action}:{primary_recovery_confidence:.2f}"
        if primary_recovery_action is not None
        and primary_recovery_confidence is not None
        else "none"
    )
    human_summary = (
        f"strategy={strategy.value}; "
        f"orchestrate_status={orchestration_status}; "
        f"actions={action_text}; "
        f"profile=execute:{execution_profile.execute_max_loops}/auto_steps:{execution_profile.auto_advance_max_steps}; "
        f"next_action={status_before.next_action or 'none'}->{status_after.next_action or 'none'}; "
        f"pending_confirmation={status_before.has_pending_confirmation}->{status_after.has_pending_confirmation}; "
        f"workitems_after={status_after.workitem_total}; "
        f"reason={reason_text}; "
        f"primary_recovery={primary_recovery_text}; "
        f"recovery_actions={recovery_text}"
    )
    return WorkflowRunOrchestrateDecisionReport(
        human_summary=human_summary,
        machine=machine,
    )
