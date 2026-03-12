from __future__ import annotations

from fastapi import HTTPException

from control_center.models import (
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    DecomposeBootstrapAggregateStatusResponse,
    DecomposeBootstrapPendingWorkflowResponse,
    DecomposeBootstrapPreviewResponse,
    WorkflowRunRoutingDecisionsResponse,
)
from control_center.services.workflow_decompose_runtime_helpers import (
    build_pending_decomposition_view,
    extract_pending_confirmation_state,
    extract_pending_modules,
    normalize_pending_module_task_packages,
)
from control_center.services.workflow_decompose_runtime_policy import (
    apply_confirmation_approved_metadata,
    apply_confirmation_rejected_metadata,
    build_confirmation_response,
    summarize_advance_loop_steps,
    validate_confirmation_token,
    validate_expected_modules,
)


async def get_decompose_bootstrap_pending(
    service,
    run_id: str,
) -> DecomposeBootstrapPendingWorkflowResponse:
    scheduler = service._workflow_scheduler_provider()
    try:
        run = scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pending = service._get_pending_decomposition_handler(run)
    if pending is None:
        return DecomposeBootstrapPendingWorkflowResponse(
            run_id=run_id,
            has_pending_confirmation=False,
        )

    pending_view = build_pending_decomposition_view(
        pending,
        optional_text_handler=service._optional_text_handler,
        normalize_module_candidates_handler=service._normalize_module_candidates_handler,
    )
    (
        preview_ready,
        preview_stale,
        preview_generated_at,
        preview_fingerprint,
    ) = service._get_preview_snapshot_status_handler(run, pending)

    return DecomposeBootstrapPendingWorkflowResponse(
        run_id=run_id,
        has_pending_confirmation=pending_view.confirmation_status == "pending",
        confirmation_status=pending_view.confirmation_status,
        confirmation_token=pending_view.confirmation_token,
        requested_by=pending_view.requested_by,
        requested_at=pending_view.requested_at,
        confirmed_by=pending_view.confirmed_by,
        confirmed_at=pending_view.confirmed_at,
        reason=pending_view.reason,
        requirements=pending_view.requirements,
        module_hints=pending_view.module_hints,
        max_modules=pending_view.max_modules,
        modules=pending_view.modules,
        chief_summary=pending_view.chief_summary,
        chief_agent=pending_view.chief_agent,
        chief_trace_id=pending_view.chief_trace_id,
        chief_metadata=pending_view.chief_metadata,
        preview_ready=preview_ready,
        preview_stale=preview_stale,
        preview_generated_at=preview_generated_at,
        preview_fingerprint=preview_fingerprint,
    )


async def get_decompose_bootstrap_aggregate_status(
    service,
    run_id: str,
) -> DecomposeBootstrapAggregateStatusResponse:
    scheduler = service._workflow_scheduler_provider()
    try:
        run = scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service._build_decompose_aggregate_status_handler(run_id, run)


async def get_workflow_run_routing_decisions(
    service,
    run_id: str,
) -> WorkflowRunRoutingDecisionsResponse:
    scheduler = service._workflow_scheduler_provider()
    try:
        run = scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service._build_routing_decisions_response_handler(run_id, run)


async def get_decompose_bootstrap_preview(
    service,
    run_id: str,
    refresh: bool = False,
) -> DecomposeBootstrapPreviewResponse:
    scheduler = service._workflow_scheduler_provider()
    try:
        run = scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return service._get_or_build_decompose_bootstrap_preview_handler(
            run_id,
            run,
            refresh,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if detail == "no decomposition data to preview" else 422
        raise HTTPException(status_code=status_code, detail=detail) from exc


async def advance_decompose_bootstrap_run_loop(
    service,
    run_id: str,
    payload: DecomposeBootstrapAdvanceLoopRequest,
) -> DecomposeBootstrapAdvanceLoopResponse:
    scheduler = service._workflow_scheduler_provider()
    try:
        scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    steps = []
    halted_reason = "max_steps_reached"
    for _ in range(payload.max_steps):
        step = await service._advance_decompose_bootstrap_once(
            run_id,
            confirmed_by=payload.confirmed_by,
            confirmation_token=payload.confirmation_token,
            expected_modules=payload.expected_modules,
            execute_max_loops=payload.execute_max_loops,
            force_refresh_preview=payload.force_refresh_preview,
        )
        steps.append(step)
        if step.action_status == "blocked":
            halted_reason = "blocked"
            break
        if step.action_status == "noop":
            halted_reason = "noop"
            break
        if payload.stop_when_bootstrap_finished and step.status_after.bootstrap_finished:
            halted_reason = "bootstrap_finished"
            break

    fallback_final_status = service._build_decompose_aggregate_status_handler(
        run_id=run_id,
        run=scheduler.get_run(run_id),
    )
    return summarize_advance_loop_steps(
        run_id=run_id,
        steps=steps,
        fallback_final_status=fallback_final_status,
        halted_reason=halted_reason,
    )


async def confirm_decompose_bootstrap_workflow_run(
    service,
    run_id: str,
    payload: ConfirmDecomposeBootstrapWorkflowRequest,
) -> ConfirmDecomposeBootstrapWorkflowResponse:
    scheduler = service._workflow_scheduler_provider()
    try:
        run = scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pending = service._get_pending_decomposition_handler(run)
    if pending is None:
        raise HTTPException(status_code=409, detail="no pending decomposition to confirm")

    try:
        confirmation, current_status, token = extract_pending_confirmation_state(pending)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if current_status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"decomposition confirmation not pending: {current_status or 'unknown'}",
        )

    try:
        validate_confirmation_token(
            payload_confirmation_token=payload.confirmation_token,
            stored_token=token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        modules = extract_pending_modules(
            pending,
            normalize_module_candidates_handler=service._normalize_module_candidates_handler,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        validate_expected_modules(
            payload_expected_modules=payload.expected_modules,
            modules=modules,
            normalize_module_candidates_handler=(
                service._normalize_module_candidates_handler
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    module_task_packages = normalize_pending_module_task_packages(
        pending.get("module_task_packages")
    )

    confirmation["confirmed_by"] = payload.confirmed_by
    confirmation["confirmed_at"] = service._now_utc_handler().isoformat()
    if payload.reason:
        confirmation["reason"] = payload.reason

    if not payload.approved:
        apply_confirmation_rejected_metadata(
            run=run,
            pending=pending,
            confirmation=confirmation,
        )
        scheduler.persist_run(run_id)
        return build_confirmation_response(
            run_id=run_id,
            approved=False,
            token=token,
            payload=payload,
            modules=modules,
            workitems=[],
        )

    try:
        bootstrap = service._workflow_engine_provider().bootstrap_standard_pipeline(
            run_id,
            modules,
            module_task_packages=module_task_packages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    apply_confirmation_approved_metadata(
        run=run,
        pending=pending,
        confirmation=confirmation,
    )
    scheduler.persist_run(run_id)
    return build_confirmation_response(
        run_id=run_id,
        approved=True,
        token=token,
        payload=payload,
        modules=modules,
        workitems=bootstrap.workitems,
    )
