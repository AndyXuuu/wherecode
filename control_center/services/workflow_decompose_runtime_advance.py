from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import HTTPException

from control_center.models import (
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapPreviewResponse,
    ExecuteWorkflowRunResponse,
    WorkflowRun,
)


@dataclass(frozen=True, slots=True)
class AdvanceActionExecutionResult:
    action_status: str
    reason: str | None
    preview: DecomposeBootstrapPreviewResponse | None
    confirmation: ConfirmDecomposeBootstrapWorkflowResponse | None
    execute: ExecuteWorkflowRunResponse | None


async def execute_advance_action(
    *,
    action_taken: str,
    run_id: str,
    run: WorkflowRun,
    confirmed_by: str | None,
    confirmation_token: str | None,
    expected_modules: list[str],
    execute_max_loops: int,
    force_refresh_preview: bool,
    get_or_build_decompose_bootstrap_preview_handler: Callable[
        [str, WorkflowRun, bool], DecomposeBootstrapPreviewResponse
    ],
    confirm_decompose_bootstrap_workflow_run_handler: Callable[
        [str, ConfirmDecomposeBootstrapWorkflowRequest],
        Awaitable[ConfirmDecomposeBootstrapWorkflowResponse],
    ],
    select_decomposition_for_preview_handler: Callable[
        [WorkflowRun], tuple[dict[str, object] | None, str]
    ],
    extract_preview_modules_handler: Callable[[dict[str, object]], list[str]],
    extract_module_task_packages_from_decomposition_handler: Callable[
        [dict[str, object]], dict[str, list[dict[str, object]]] | None
    ],
    bootstrap_pipeline_handler: Callable[
        [str, list[str], dict[str, list[dict[str, object]]] | None],
        object,
    ],
    execute_until_blocked_handler: Callable[[str, int], Awaitable[ExecuteWorkflowRunResponse]],
    tick_workitems_handler: Callable[[str], object],
) -> AdvanceActionExecutionResult:
    preview_result: DecomposeBootstrapPreviewResponse | None = None
    confirmation_result: ConfirmDecomposeBootstrapWorkflowResponse | None = None
    execute_result: ExecuteWorkflowRunResponse | None = None
    action_status = "noop"
    reason: str | None = None

    try:
        if action_taken in {"generate_preview", "refresh_preview"}:
            preview_result = get_or_build_decompose_bootstrap_preview_handler(
                run_id,
                run,
                force_refresh_preview or action_taken == "refresh_preview",
            )
            action_status = "executed"
        elif action_taken == "confirm_or_reject_decomposition":
            if not confirmed_by:
                action_status = "blocked"
                reason = "confirmed_by is required to auto-confirm pending decomposition"
            else:
                confirmation_result = await confirm_decompose_bootstrap_workflow_run_handler(
                    run_id,
                    ConfirmDecomposeBootstrapWorkflowRequest(
                        confirmed_by=confirmed_by,
                        approved=True,
                        expected_modules=expected_modules,
                        confirmation_token=confirmation_token,
                    ),
                )
                action_status = "executed"
        elif action_taken == "bootstrap_pipeline":
            decomposition, _ = select_decomposition_for_preview_handler(run)
            if decomposition is None:
                action_status = "blocked"
                reason = "no decomposition record for bootstrap"
            else:
                modules = extract_preview_modules_handler(decomposition)
                if not modules:
                    action_status = "blocked"
                    reason = "decomposition has no valid modules"
                else:
                    bootstrap_pipeline_handler(
                        run_id,
                        modules,
                        extract_module_task_packages_from_decomposition_handler(
                            decomposition
                        ),
                    )
                    action_status = "executed"
        elif action_taken == "execute_workflow_run":
            execute_result = await execute_until_blocked_handler(
                run_id,
                execute_max_loops,
            )
            action_status = "executed"
        elif action_taken == "wait_or_unblock_workitems":
            tick_workitems_handler(run_id)
            action_status = "executed"
        elif action_taken == "trigger_decompose_bootstrap":
            action_status = "blocked"
            reason = "decompose-bootstrap request payload is required"
        else:
            action_status = "noop"
    except HTTPException as exc:
        if exc.status_code in {409, 422}:
            action_status = "blocked"
            reason = str(exc.detail)
        else:
            raise
    except ValueError as exc:
        action_status = "blocked"
        reason = str(exc)

    return AdvanceActionExecutionResult(
        action_status=action_status,
        reason=reason,
        preview=preview_result,
        confirmation=confirmation_result,
        execute=execute_result,
    )
