from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapAdvanceLoopResponse,
    DecomposeBootstrapAdvanceResponse,
    DecomposeBootstrapAggregateStatusResponse,
    DecomposeBootstrapWorkflowRequest,
    DecomposeBootstrapWorkflowResponse,
    RequirementStatus,
    SDDStage,
    WorkflowRun,
)


def build_chief_action_request(
    *,
    payload: DecomposeBootstrapWorkflowRequest,
    run: WorkflowRun,
    requested_by: str,
    build_chief_decompose_prompt_handler: Callable[[str, int, list[str], str, str | None], str],
) -> ActionExecuteRequest:
    return ActionExecuteRequest(
        text=build_chief_decompose_prompt_handler(
            payload.requirements,
            payload.max_modules,
            payload.module_hints,
            run.project_id,
            run.task_id,
        ),
        role="chief-architect",
        project_id=run.project_id,
        task_id=run.task_id,
        requested_by=requested_by,
        module_key="workflow_decomposition",
    )


def build_chief_summary_text(
    chief_result: ActionExecuteResponse,
    *,
    fallback_applied: bool,
) -> str:
    if not fallback_applied:
        return chief_result.summary
    if chief_result.summary:
        return f"{chief_result.summary}; synthetic decomposition fallback applied"
    return "synthetic decomposition fallback applied"


def build_decomposition_record(
    *,
    payload: DecomposeBootstrapWorkflowRequest,
    modules: list[str],
    required_tags: list[str],
    missing_tags: list[str],
    requirement_module_map: dict[str, list[str]],
    missing_mapping_tags: list[str],
    invalid_mapping_modules: dict[str, list[str]],
    mapping_explicit: bool,
    module_task_packages: dict[str, list[dict[str, object]]],
    module_routing_decisions: dict[str, dict[str, object]],
    missing_task_package_modules: list[str],
    invalid_task_package_roles: dict[str, list[str]],
    missing_task_package_roles: dict[str, list[str]],
    task_package_explicit: bool,
    fallback_applied: bool,
    fallback_reason: str | None,
    chief_result: ActionExecuteResponse,
    chief_summary_text: str,
    chief_metadata: dict[str, object],
) -> dict[str, object]:
    return {
        "requirements": payload.requirements,
        "module_hints": payload.module_hints,
        "max_modules": payload.max_modules,
        "modules": modules,
        "required_coverage_tags": required_tags,
        "missing_coverage_tags": missing_tags,
        "requirement_module_map": requirement_module_map,
        "missing_mapping_tags": missing_mapping_tags,
        "invalid_mapping_modules": invalid_mapping_modules,
        "mapping_explicit": mapping_explicit,
        "module_task_packages": module_task_packages,
        "module_routing_decisions": module_routing_decisions,
        "missing_task_package_modules": missing_task_package_modules,
        "invalid_task_package_roles": invalid_task_package_roles,
        "missing_task_package_roles": missing_task_package_roles,
        "task_package_explicit": task_package_explicit,
        "synthetic_fallback_applied": fallback_applied,
        "synthetic_fallback_reason": fallback_reason,
        "chief_status": chief_result.status,
        "chief_summary": chief_summary_text,
        "chief_agent": chief_result.agent,
        "chief_trace_id": chief_result.trace_id,
        "chief_metadata": chief_metadata,
    }


def apply_pending_confirmation_metadata(
    *,
    run: WorkflowRun,
    decomposition_record: dict[str, object],
    requested_by: str,
    now_iso: str,
) -> str:
    confirmation_token = f"decomp_{uuid4().hex[:12]}"
    decomposition_record["confirmation"] = {
        "required": True,
        "status": "pending",
        "token": confirmation_token,
        "requested_by": requested_by,
        "requested_at": now_iso,
    }
    run.metadata["chief_decomposition"] = decomposition_record
    run.metadata["pending_decomposition"] = decomposition_record
    run.metadata.pop("decompose_bootstrap_preview", None)
    run.requirement_status = RequirementStatus.CONFIRMED
    run.current_stage = SDDStage.TASKS
    run.blocked_reason = None
    run.next_action_hint = "confirm_decomposition"
    return confirmation_token


def apply_auto_approved_confirmation_metadata(
    *,
    run: WorkflowRun,
    decomposition_record: dict[str, object],
    now_iso: str,
) -> None:
    decomposition_record["confirmation"] = {
        "required": False,
        "status": "auto-approved",
        "confirmed_by": "system",
        "confirmed_at": now_iso,
    }
    run.metadata["chief_decomposition"] = decomposition_record
    run.metadata.pop("pending_decomposition", None)
    run.metadata.pop("decompose_bootstrap_preview", None)
    run.requirement_status = RequirementStatus.CONFIRMED
    run.current_stage = SDDStage.TASKS
    run.blocked_reason = None
    run.next_action_hint = "execute_workflow_run"


def build_decompose_pending_response(
    *,
    run_id: str,
    modules: list[str],
    chief_result: ActionExecuteResponse,
    chief_summary_text: str,
    chief_metadata: dict[str, object],
    confirmation_token: str,
) -> DecomposeBootstrapWorkflowResponse:
    return DecomposeBootstrapWorkflowResponse(
        run_id=run_id,
        modules=modules,
        chief_summary=chief_summary_text,
        chief_agent=chief_result.agent,
        chief_trace_id=chief_result.trace_id,
        chief_metadata=chief_metadata,
        workitems=[],
        confirmation_required=True,
        confirmation_status="pending",
        confirmation_token=confirmation_token,
    )


def build_decompose_auto_approved_response(
    *,
    run_id: str,
    modules: list[str],
    chief_result: ActionExecuteResponse,
    chief_summary_text: str,
    chief_metadata: dict[str, object],
    workitems: list[object],
) -> DecomposeBootstrapWorkflowResponse:
    return DecomposeBootstrapWorkflowResponse(
        run_id=run_id,
        modules=modules,
        chief_summary=chief_summary_text,
        chief_agent=chief_result.agent,
        chief_trace_id=chief_result.trace_id,
        chief_metadata=chief_metadata,
        workitems=workitems,
        confirmation_required=False,
        confirmation_status="auto-approved",
        confirmation_token=None,
    )


def validate_confirmation_token(
    *,
    payload_confirmation_token: str | None,
    stored_token: str | None,
) -> None:
    if payload_confirmation_token and stored_token and payload_confirmation_token != stored_token:
        raise ValueError("confirmation token mismatch")


def validate_expected_modules(
    *,
    payload_expected_modules: list[str],
    modules: list[str],
    normalize_module_candidates_handler: Callable[[list[object]], list[str]],
) -> None:
    if not payload_expected_modules:
        return
    expected_modules = normalize_module_candidates_handler(payload_expected_modules)
    if expected_modules != modules:
        raise ValueError("expected modules mismatch with pending decomposition")


def apply_confirmation_rejected_metadata(
    *,
    run: WorkflowRun,
    pending: dict[str, object],
    confirmation: dict[str, object],
) -> None:
    confirmation["status"] = "rejected"
    run.metadata["pending_decomposition"] = pending
    run.metadata["chief_decomposition"] = pending
    run.requirement_status = RequirementStatus.BLOCKED
    run.blocked_reason = "decomposition_rejected"
    run.next_action_hint = "revise_decomposition_and_reconfirm"


def apply_confirmation_approved_metadata(
    *,
    run: WorkflowRun,
    pending: dict[str, object],
    confirmation: dict[str, object],
) -> None:
    confirmation["status"] = "approved"
    run.metadata["chief_decomposition"] = pending
    run.metadata.pop("pending_decomposition", None)
    run.requirement_status = RequirementStatus.CONFIRMED
    run.current_stage = SDDStage.TASKS
    run.blocked_reason = None
    run.next_action_hint = "execute_workflow_run"


def build_confirmation_response(
    *,
    run_id: str,
    approved: bool,
    token: str | None,
    payload: ConfirmDecomposeBootstrapWorkflowRequest,
    modules: list[str],
    workitems: list[object],
) -> ConfirmDecomposeBootstrapWorkflowResponse:
    return ConfirmDecomposeBootstrapWorkflowResponse(
        run_id=run_id,
        approved=approved,
        confirmation_status=("approved" if approved else "rejected"),
        confirmation_token=token or None,
        confirmed_by=payload.confirmed_by,
        reason=payload.reason,
        modules=modules,
        workitems=workitems,
    )


def summarize_advance_loop_steps(
    *,
    run_id: str,
    steps: list[DecomposeBootstrapAdvanceResponse],
    fallback_final_status: DecomposeBootstrapAggregateStatusResponse,
    halted_reason: str,
) -> DecomposeBootstrapAdvanceLoopResponse:
    if steps:
        final_status = steps[-1].status_after
    else:
        final_status = fallback_final_status
        halted_reason = "no_steps"

    action_status_counts: dict[str, int] = {}
    action_taken_sequence: list[str] = []
    for step in steps:
        action_taken_sequence.append(step.action_taken)
        action_status_counts[step.action_status] = (
            action_status_counts.get(step.action_status, 0) + 1
        )

    return DecomposeBootstrapAdvanceLoopResponse(
        run_id=run_id,
        steps_executed=len(steps),
        halted_reason=halted_reason,
        last_action_taken=(steps[-1].action_taken if steps else None),
        action_taken_sequence=action_taken_sequence,
        action_status_counts=action_status_counts,
        final_status=final_status,
        steps=steps,
    )
