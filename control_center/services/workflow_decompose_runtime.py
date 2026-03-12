from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

from fastapi import HTTPException

from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    DecomposeBootstrapAdvanceRequest,
    DecomposeBootstrapAdvanceResponse,
    DecomposeBootstrapAggregateStatusResponse,
    DecomposeBootstrapPendingWorkflowResponse,
    DecomposeBootstrapPreviewResponse,
    DecomposeBootstrapWorkflowRequest,
    DecomposeBootstrapWorkflowResponse,
    ExecuteWorkflowRunResponse,
    WorkflowRun,
    WorkflowRunRoutingDecisionsResponse,
)
from control_center.services.action_layer_client import ActionLayerClientError
from control_center.services.workflow_decompose_runtime_helpers import (
    resolve_decomposition_from_chief_result,
)
from control_center.services.workflow_decompose_runtime_ops import (
    advance_decompose_bootstrap_run_loop as advance_decompose_bootstrap_run_loop_impl,
    confirm_decompose_bootstrap_workflow_run as confirm_decompose_bootstrap_workflow_run_impl,
    get_decompose_bootstrap_aggregate_status as get_decompose_bootstrap_aggregate_status_impl,
    get_decompose_bootstrap_pending as get_decompose_bootstrap_pending_impl,
    get_decompose_bootstrap_preview as get_decompose_bootstrap_preview_impl,
    get_workflow_run_routing_decisions as get_workflow_run_routing_decisions_impl,
)
from control_center.services.workflow_decompose_runtime_policy import (
    apply_auto_approved_confirmation_metadata,
    apply_pending_confirmation_metadata,
    build_chief_action_request,
    build_chief_summary_text,
    build_decompose_auto_approved_response,
    build_decompose_pending_response,
    build_decomposition_record,
)
from control_center.services.workflow_decompose_runtime_advance import (
    execute_advance_action,
)
from control_center.services.workflow_engine import WorkflowEngine
from control_center.services.workflow_scheduler import WorkflowScheduler


class WorkflowDecomposeRuntimeService:
    def __init__(
        self,
        *,
        workflow_scheduler_provider: Callable[[], WorkflowScheduler],
        workflow_engine_provider: Callable[[], WorkflowEngine],
        now_utc_handler: Callable[[], datetime],
        optional_text_handler: Callable[[object], str | None],
        get_pending_decomposition_handler: Callable[[WorkflowRun], dict[str, object] | None],
        get_pending_confirmation_status_handler: Callable[[dict[str, object]], str],
        normalize_module_candidates_handler: Callable[[list[object]], list[str]],
        get_preview_snapshot_status_handler: Callable[
            [WorkflowRun, dict[str, object]],
            tuple[bool, bool, str | None, str | None],
        ],
        build_decompose_aggregate_status_handler: Callable[
            [str, WorkflowRun], DecomposeBootstrapAggregateStatusResponse
        ],
        build_routing_decisions_response_handler: Callable[
            [str, WorkflowRun], WorkflowRunRoutingDecisionsResponse
        ],
        get_or_build_decompose_bootstrap_preview_handler: Callable[
            [str, WorkflowRun, bool], DecomposeBootstrapPreviewResponse
        ],
        select_decomposition_for_preview_handler: Callable[
            [WorkflowRun], tuple[dict[str, object] | None, str]
        ],
        extract_preview_modules_handler: Callable[[dict[str, object]], list[str]],
        extract_module_task_packages_from_decomposition_handler: Callable[
            [dict[str, object]], dict[str, list[dict[str, object]]] | None
        ],
        build_chief_decompose_prompt_handler: Callable[
            [str, int, list[str], str, str | None], str
        ],
        execute_chief_action_handler: Callable[
            [ActionExecuteRequest], Awaitable[ActionExecuteResponse]
        ],
        build_synthetic_decomposition_fallback_handler: Callable[
            [str, list[str], int], dict[str, object] | None
        ],
        extract_modules_from_chief_response_handler: Callable[
            [ActionExecuteResponse, int], list[str]
        ],
        validate_decomposition_coverage_handler: Callable[
            [str, list[str], list[str], dict[str, object]],
            tuple[list[str], list[str]],
        ],
        validate_requirement_module_mapping_handler: Callable[
            [list[str], list[str], dict[str, object]],
            tuple[dict[str, list[str]], list[str], dict[str, list[str]], bool],
        ],
        validate_module_task_packages_handler: Callable[
            [list[str], dict[str, object]],
            tuple[
                dict[str, list[dict[str, object]]],
                list[str],
                dict[str, list[str]],
                dict[str, list[str]],
                bool,
            ],
        ],
        dev_routing_apply_handler: Callable[
            [list[str], dict[str, list[dict[str, object]]], dict[str, object]],
            tuple[dict[str, list[dict[str, object]]], dict[str, dict[str, object]]],
        ],
        decompose_allow_synthetic_fallback_provider: Callable[[], bool],
        decompose_require_explicit_map_provider: Callable[[], bool],
        decompose_require_task_package_provider: Callable[[], bool],
        decompose_require_confirmation_provider: Callable[[], bool],
    ) -> None:
        self._workflow_scheduler_provider = workflow_scheduler_provider
        self._workflow_engine_provider = workflow_engine_provider
        self._now_utc_handler = now_utc_handler
        self._optional_text_handler = optional_text_handler
        self._get_pending_decomposition_handler = get_pending_decomposition_handler
        self._get_pending_confirmation_status_handler = (
            get_pending_confirmation_status_handler
        )
        self._normalize_module_candidates_handler = normalize_module_candidates_handler
        self._get_preview_snapshot_status_handler = get_preview_snapshot_status_handler
        self._build_decompose_aggregate_status_handler = (
            build_decompose_aggregate_status_handler
        )
        self._build_routing_decisions_response_handler = (
            build_routing_decisions_response_handler
        )
        self._get_or_build_decompose_bootstrap_preview_handler = (
            get_or_build_decompose_bootstrap_preview_handler
        )
        self._select_decomposition_for_preview_handler = (
            select_decomposition_for_preview_handler
        )
        self._extract_preview_modules_handler = extract_preview_modules_handler
        self._extract_module_task_packages_from_decomposition_handler = (
            extract_module_task_packages_from_decomposition_handler
        )
        self._build_chief_decompose_prompt_handler = build_chief_decompose_prompt_handler
        self._execute_chief_action_handler = execute_chief_action_handler
        self._build_synthetic_decomposition_fallback_handler = (
            build_synthetic_decomposition_fallback_handler
        )
        self._extract_modules_from_chief_response_handler = (
            extract_modules_from_chief_response_handler
        )
        self._validate_decomposition_coverage_handler = (
            validate_decomposition_coverage_handler
        )
        self._validate_requirement_module_mapping_handler = (
            validate_requirement_module_mapping_handler
        )
        self._validate_module_task_packages_handler = (
            validate_module_task_packages_handler
        )
        self._dev_routing_apply_handler = dev_routing_apply_handler
        self._decompose_allow_synthetic_fallback_provider = (
            decompose_allow_synthetic_fallback_provider
        )
        self._decompose_require_explicit_map_provider = (
            decompose_require_explicit_map_provider
        )
        self._decompose_require_task_package_provider = (
            decompose_require_task_package_provider
        )
        self._decompose_require_confirmation_provider = (
            decompose_require_confirmation_provider
        )

    async def decompose_bootstrap_workflow_run(
        self,
        run_id: str,
        payload: DecomposeBootstrapWorkflowRequest,
    ) -> DecomposeBootstrapWorkflowResponse:
        scheduler = self._workflow_scheduler_provider()
        try:
            run = scheduler.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        pending = self._get_pending_decomposition_handler(run)
        if pending is not None and self._get_pending_confirmation_status_handler(pending) == "pending":
            raise HTTPException(
                status_code=409,
                detail="pending decomposition confirmation exists",
            )

        requested_by = payload.requested_by or run.requested_by or "control-center"
        action_request = build_chief_action_request(
            payload=payload,
            run=run,
            requested_by=requested_by,
            build_chief_decompose_prompt_handler=(
                self._build_chief_decompose_prompt_handler
            ),
        )

        try:
            chief_result = await self._execute_chief_action_handler(action_request)
        except ActionLayerClientError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        chief_metadata: dict[str, object] = (
            dict(chief_result.metadata) if isinstance(chief_result.metadata, dict) else {}
        )
        try:
            resolution = resolve_decomposition_from_chief_result(
                chief_result=chief_result,
                payload=payload,
                chief_metadata=chief_metadata,
                decompose_allow_synthetic_fallback=(
                    self._decompose_allow_synthetic_fallback_provider()
                ),
                decompose_require_explicit_map=(
                    self._decompose_require_explicit_map_provider()
                ),
                decompose_require_task_package=(
                    self._decompose_require_task_package_provider()
                ),
                build_synthetic_decomposition_fallback_handler=(
                    self._build_synthetic_decomposition_fallback_handler
                ),
                extract_modules_from_chief_response_handler=(
                    self._extract_modules_from_chief_response_handler
                ),
                validate_decomposition_coverage_handler=(
                    self._validate_decomposition_coverage_handler
                ),
                validate_requirement_module_mapping_handler=(
                    self._validate_requirement_module_mapping_handler
                ),
                validate_module_task_packages_handler=(
                    self._validate_module_task_packages_handler
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        modules = resolution.modules
        required_tags = resolution.required_tags
        missing_tags = resolution.missing_tags
        requirement_module_map = resolution.requirement_module_map
        missing_mapping_tags = resolution.missing_mapping_tags
        invalid_mapping_modules = resolution.invalid_mapping_modules
        mapping_explicit = resolution.mapping_explicit
        module_task_packages = resolution.module_task_packages
        missing_task_package_modules = resolution.missing_task_package_modules
        invalid_task_package_roles = resolution.invalid_task_package_roles
        missing_task_package_roles = resolution.missing_task_package_roles
        task_package_explicit = resolution.task_package_explicit
        chief_metadata = resolution.chief_metadata
        fallback_applied = resolution.fallback_applied
        fallback_reason = resolution.fallback_reason

        module_task_packages, module_routing_decisions = self._dev_routing_apply_handler(
            modules,
            module_task_packages,
            chief_metadata,
        )

        chief_summary_text = build_chief_summary_text(
            chief_result,
            fallback_applied=fallback_applied,
        )

        now_iso = self._now_utc_handler().isoformat()
        decomposition_record = build_decomposition_record(
            payload=payload,
            modules=modules,
            required_tags=required_tags,
            missing_tags=missing_tags,
            requirement_module_map=requirement_module_map,
            missing_mapping_tags=missing_mapping_tags,
            invalid_mapping_modules=invalid_mapping_modules,
            mapping_explicit=mapping_explicit,
            module_task_packages=module_task_packages,
            module_routing_decisions=module_routing_decisions,
            missing_task_package_modules=missing_task_package_modules,
            invalid_task_package_roles=invalid_task_package_roles,
            missing_task_package_roles=missing_task_package_roles,
            task_package_explicit=task_package_explicit,
            fallback_applied=fallback_applied,
            fallback_reason=fallback_reason,
            chief_result=chief_result,
            chief_summary_text=chief_summary_text,
            chief_metadata=chief_metadata,
        )
        if self._decompose_require_confirmation_provider():
            confirmation_token = apply_pending_confirmation_metadata(
                run=run,
                decomposition_record=decomposition_record,
                requested_by=requested_by,
                now_iso=now_iso,
            )
            scheduler.persist_run(run_id)
            return build_decompose_pending_response(
                run_id=run_id,
                modules=modules,
                chief_result=chief_result,
                chief_summary_text=chief_summary_text,
                chief_metadata=chief_metadata,
                confirmation_token=confirmation_token,
            )

        try:
            bootstrap = self._workflow_engine_provider().bootstrap_standard_pipeline(
                run_id,
                modules,
                module_task_packages=module_task_packages,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        apply_auto_approved_confirmation_metadata(
            run=run,
            decomposition_record=decomposition_record,
            now_iso=now_iso,
        )
        scheduler.persist_run(run_id)

        return build_decompose_auto_approved_response(
            run_id=run_id,
            modules=modules,
            chief_result=chief_result,
            chief_summary_text=chief_summary_text,
            chief_metadata=chief_metadata,
            workitems=bootstrap.workitems,
        )

    async def get_decompose_bootstrap_pending(
        self,
        run_id: str,
    ) -> DecomposeBootstrapPendingWorkflowResponse:
        return await get_decompose_bootstrap_pending_impl(self, run_id)

    async def get_decompose_bootstrap_aggregate_status(
        self,
        run_id: str,
    ) -> DecomposeBootstrapAggregateStatusResponse:
        return await get_decompose_bootstrap_aggregate_status_impl(self, run_id)

    async def get_workflow_run_routing_decisions(
        self,
        run_id: str,
    ) -> WorkflowRunRoutingDecisionsResponse:
        return await get_workflow_run_routing_decisions_impl(self, run_id)

    async def get_decompose_bootstrap_preview(
        self,
        run_id: str,
        refresh: bool = False,
    ) -> DecomposeBootstrapPreviewResponse:
        return await get_decompose_bootstrap_preview_impl(self, run_id, refresh)

    async def _advance_decompose_bootstrap_once(
        self,
        run_id: str,
        *,
        confirmed_by: str | None,
        confirmation_token: str | None,
        expected_modules: list[str],
        execute_max_loops: int,
        force_refresh_preview: bool,
    ) -> DecomposeBootstrapAdvanceResponse:
        scheduler = self._workflow_scheduler_provider()
        run = scheduler.get_run(run_id)
        status_before = self._build_decompose_aggregate_status_handler(run_id, run)
        action_taken = status_before.next_action or "review_results"
        execution_result = await execute_advance_action(
            action_taken=action_taken,
            run_id=run_id,
            run=run,
            confirmed_by=confirmed_by,
            confirmation_token=confirmation_token,
            expected_modules=expected_modules,
            execute_max_loops=execute_max_loops,
            force_refresh_preview=force_refresh_preview,
            get_or_build_decompose_bootstrap_preview_handler=(
                self._get_or_build_decompose_bootstrap_preview_handler
            ),
            confirm_decompose_bootstrap_workflow_run_handler=(
                self.confirm_decompose_bootstrap_workflow_run
            ),
            select_decomposition_for_preview_handler=(
                self._select_decomposition_for_preview_handler
            ),
            extract_preview_modules_handler=self._extract_preview_modules_handler,
            extract_module_task_packages_from_decomposition_handler=(
                self._extract_module_task_packages_from_decomposition_handler
            ),
            bootstrap_pipeline_handler=(
                lambda target_run_id, modules, module_task_packages: (
                    self._workflow_engine_provider().bootstrap_standard_pipeline(
                        target_run_id,
                        modules,
                        module_task_packages=module_task_packages,
                    )
                )
            ),
            execute_until_blocked_handler=(
                lambda target_run_id, max_loops: (
                    self._workflow_engine_provider().execute_until_blocked(
                        run_id=target_run_id,
                        max_loops=max_loops,
                    )
                )
            ),
            tick_workitems_handler=lambda target_run_id: scheduler.tick(target_run_id),
        )

        run_after = scheduler.get_run(run_id)
        status_after = self._build_decompose_aggregate_status_handler(run_id, run_after)
        return DecomposeBootstrapAdvanceResponse(
            run_id=run_id,
            action_taken=action_taken,
            action_status=execution_result.action_status,
            reason=execution_result.reason,
            status_before=status_before,
            status_after=status_after,
            preview=execution_result.preview,
            confirmation=execution_result.confirmation,
            execute=execution_result.execute,
        )

    async def advance_decompose_bootstrap_run(
        self,
        run_id: str,
        payload: DecomposeBootstrapAdvanceRequest,
    ) -> DecomposeBootstrapAdvanceResponse:
        try:
            return await self._advance_decompose_bootstrap_once(
                run_id,
                confirmed_by=payload.confirmed_by,
                confirmation_token=payload.confirmation_token,
                expected_modules=payload.expected_modules,
                execute_max_loops=payload.max_loops,
                force_refresh_preview=payload.force_refresh_preview,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def advance_decompose_bootstrap_run_loop(
        self,
        run_id: str,
        payload: DecomposeBootstrapAdvanceLoopRequest,
    ) -> DecomposeBootstrapAdvanceLoopResponse:
        return await advance_decompose_bootstrap_run_loop_impl(self, run_id, payload)

    async def confirm_decompose_bootstrap_workflow_run(
        self,
        run_id: str,
        payload: ConfirmDecomposeBootstrapWorkflowRequest,
    ) -> ConfirmDecomposeBootstrapWorkflowResponse:
        return await confirm_decompose_bootstrap_workflow_run_impl(
            self,
            run_id,
            payload,
        )
