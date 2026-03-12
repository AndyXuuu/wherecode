from __future__ import annotations

from collections.abc import Callable
from typing import Any

from control_center.models import (
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAggregateStatusResponse,
    ExecuteWorkflowRunRequest,
    WorkflowRunOrchestrateDecomposePayload,
    WorkflowRunOrchestrateExecutionProfile,
    WorkflowRunOrchestrateRecoveryExecuteResponse,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateRequest,
    WorkflowRunOrchestrateResponse,
    WorkflowRunOrchestrateStrategy,
    WorkflowRunOrchestrateTelemetryRecord,
)


def derive_execution_profile(
    *,
    payload: WorkflowRunOrchestrateRequest,
    status_before: DecomposeBootstrapAggregateStatusResponse,
) -> WorkflowRunOrchestrateExecutionProfile:
    strategy = payload.strategy
    execute_max_loops = payload.execute_max_loops
    auto_advance_max_steps = payload.auto_advance_max_steps
    baseline_auto_advance_execute_max_loops = (
        payload.auto_advance_execute_max_loops
        if payload.auto_advance_execute_max_loops is not None
        else execute_max_loops
    )
    auto_advance_execute_max_loops = baseline_auto_advance_execute_max_loops
    auto_advance_force_refresh_preview = payload.auto_advance_force_refresh_preview
    if strategy == WorkflowRunOrchestrateStrategy.SAFE:
        execute_max_loops = min(execute_max_loops, 12)
        auto_advance_max_steps = min(auto_advance_max_steps, 5)
        auto_advance_execute_max_loops = min(
            baseline_auto_advance_execute_max_loops,
            12,
        )
        auto_advance_force_refresh_preview = True
    elif strategy == WorkflowRunOrchestrateStrategy.BALANCED:
        execute_max_loops = min(execute_max_loops, 16)
        auto_advance_max_steps = min(auto_advance_max_steps, 7)
        auto_advance_execute_max_loops = min(
            baseline_auto_advance_execute_max_loops,
            16,
        )
        auto_advance_force_refresh_preview = (
            auto_advance_force_refresh_preview or status_before.preview_stale
        )

    return WorkflowRunOrchestrateExecutionProfile(
        auto_advance_decompose=payload.auto_advance_decompose,
        execute_max_loops=execute_max_loops,
        auto_advance_max_steps=auto_advance_max_steps,
        auto_advance_execute_max_loops=auto_advance_execute_max_loops,
        auto_advance_force_refresh_preview=auto_advance_force_refresh_preview,
    )


def resolve_decompose_payload(
    payload: WorkflowRunOrchestrateRequest,
) -> WorkflowRunOrchestrateDecomposePayload | None:
    decompose_payload = payload.decompose_payload
    if decompose_payload is not None:
        return decompose_payload
    inline_requirements = (payload.requirements or "").strip()
    if not inline_requirements:
        return None
    return WorkflowRunOrchestrateDecomposePayload(
        requirements=inline_requirements,
        module_hints=payload.module_hints,
        max_modules=payload.max_modules,
        requested_by=payload.requested_by,
    )


def build_orchestrate_execute_request(
    *,
    payload: WorkflowRunOrchestrateRequest,
    profile: WorkflowRunOrchestrateExecutionProfile,
) -> ExecuteWorkflowRunRequest:
    return ExecuteWorkflowRunRequest(
        max_loops=profile.execute_max_loops,
        auto_advance_decompose=payload.auto_advance_decompose,
        auto_advance_max_steps=profile.auto_advance_max_steps,
        auto_advance_execute_max_loops=profile.auto_advance_execute_max_loops,
        auto_advance_force_refresh_preview=profile.auto_advance_force_refresh_preview,
        decompose_confirmed_by=payload.decompose_confirmed_by,
        decompose_confirmation_token=payload.decompose_confirmation_token,
        decompose_expected_modules=payload.decompose_expected_modules,
    )


def build_recovery_advance_loop_request(
    payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
) -> DecomposeBootstrapAdvanceLoopRequest:
    return DecomposeBootstrapAdvanceLoopRequest(
        confirmed_by=payload.confirmed_by,
        confirmation_token=payload.confirmation_token,
        expected_modules=payload.expected_modules,
        execute_max_loops=payload.execute_max_loops,
        force_refresh_preview=payload.auto_advance_force_refresh_preview,
        max_steps=payload.advance_loop_max_steps,
        stop_when_bootstrap_finished=True,
    )


def build_recovery_execute_request(
    payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
) -> ExecuteWorkflowRunRequest:
    return ExecuteWorkflowRunRequest(
        max_loops=payload.execute_max_loops,
        auto_advance_decompose=payload.auto_advance_decompose,
        auto_advance_max_steps=payload.auto_advance_max_steps,
        auto_advance_execute_max_loops=payload.auto_advance_execute_max_loops,
        auto_advance_force_refresh_preview=payload.auto_advance_force_refresh_preview,
        decompose_confirmed_by=payload.confirmed_by,
        decompose_confirmation_token=payload.confirmation_token,
        decompose_expected_modules=payload.expected_modules,
    )


def build_recovery_orchestrate_request(
    *,
    payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
    requirements: str | None,
    decompose_payload: WorkflowRunOrchestrateDecomposePayload | None,
) -> WorkflowRunOrchestrateRequest:
    return WorkflowRunOrchestrateRequest(
        strategy=payload.strategy,
        requirements=requirements,
        module_hints=payload.module_hints,
        max_modules=payload.max_modules,
        requested_by=payload.requested_by,
        decompose_payload=decompose_payload,
        force_redecompose=False,
        execute=payload.execute,
        execute_max_loops=payload.execute_max_loops,
        auto_advance_decompose=payload.auto_advance_decompose,
        auto_advance_max_steps=payload.auto_advance_max_steps,
        auto_advance_execute_max_loops=payload.auto_advance_execute_max_loops,
        auto_advance_force_refresh_preview=payload.auto_advance_force_refresh_preview,
        decompose_confirmed_by=payload.confirmed_by,
        decompose_confirmation_token=payload.confirmation_token,
        decompose_expected_modules=payload.expected_modules,
    )


def resolve_latest_confirmation_token(
    *,
    pending: dict[str, Any],
    optional_text_handler: Callable[[object], str | None],
) -> str | None:
    confirmation = pending.get("confirmation")
    if isinstance(confirmation, dict):
        return optional_text_handler(confirmation.get("token"))
    return None


def build_recovery_response(
    *,
    run_id: str,
    action_source: str,
    selected_action: str | None,
    action_status: str,
    reason: str | None,
    restarted_run_id: str | None,
    restarted_run_status: str | None,
    latest_record_before: WorkflowRunOrchestrateTelemetryRecord | None,
    orchestrate: WorkflowRunOrchestrateResponse | None,
    preview: object | None,
    confirmation: object | None,
    advance_loop: object | None,
    execute: object | None,
) -> WorkflowRunOrchestrateRecoveryExecuteResponse:
    return WorkflowRunOrchestrateRecoveryExecuteResponse(
        run_id=run_id,
        action_source=action_source,
        selected_action=selected_action,
        action_status=action_status,
        reason=reason,
        restarted_run_id=restarted_run_id,
        restarted_run_status=restarted_run_status,
        latest_record_before=latest_record_before,
        orchestrate=orchestrate,
        preview=preview,
        confirmation=confirmation,
        advance_loop=advance_loop,
        execute=execute,
    )
