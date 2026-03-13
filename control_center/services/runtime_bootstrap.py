from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from action_layer.services import AgentRegistry

from control_center.executors import ExecutorService
from control_center.models import ActionExecuteRequest, ActionExecuteResponse
from control_center.services.agent_router import AgentRouter
from control_center.services.agent_rules_registry import AgentRulesRegistryService
from control_center.services.command_dispatch import CommandDispatchService
from control_center.services.command_orchestration_policy import (
    CommandOrchestrationPolicyService,
)
from control_center.services.config_bootstrap import ControlCenterBootstrapConfig
from control_center.services.dev_routing_matrix import (
    DevRoutingMatrixService,
    normalize_text_list,
)
from control_center.services.metrics_alert_policy_store import MetricsAlertPolicyStore
from control_center.services.metrics_authorization import MetricsAuthorizationService
from control_center.services.orchestrator import InMemoryOrchestrator
from control_center.services.sqlite_state_store import SQLiteStateStore
from control_center.services.workflow_api_handlers import WorkflowAPIHandlersService
from control_center.services.workflow_decompose_helpers import (
    WorkflowDecomposeHelpersService,
)
from control_center.services.workflow_decompose_preview_support import (
    WorkflowDecomposePreviewSupportService,
)
from control_center.services.workflow_decompose_runtime import WorkflowDecomposeRuntimeService
from control_center.services.workflow_decompose_support import WorkflowDecomposeSupportService
from control_center.services.workflow_engine import WorkflowEngine
from control_center.services.workflow_execution_runtime import WorkflowExecutionRuntimeService
from control_center.services.workflow_orchestration_runtime import (
    WorkflowOrchestrationRuntimeService,
)
from control_center.services.workflow_orchestration_support import (
    WorkflowOrchestrationSupportService,
)
from control_center.services.workflow_scheduler import WorkflowScheduler


@dataclass(slots=True)
class ControlCenterRuntimeBundle:
    state_store: SQLiteStateStore | None
    store: InMemoryOrchestrator
    workflow_scheduler: WorkflowScheduler
    workflow_engine: WorkflowEngine
    command_dispatch_service: CommandDispatchService
    workflow_api_handlers_service: WorkflowAPIHandlersService
    command_orchestration_policy_service: CommandOrchestrationPolicyService
    agent_rules_registry_service: AgentRulesRegistryService
    metrics_alert_policy_store: MetricsAlertPolicyStore
    metrics_authorization_service: MetricsAuthorizationService


def _must_have_service(value: object, *, name: str) -> object:
    if value is None:
        raise RuntimeError(f"{name} not initialized")
    return value


def build_control_center_runtime(
    *,
    bootstrap_config: ControlCenterBootstrapConfig,
    logger: logging.Logger,
    agent_router: AgentRouter,
    action_layer_execute_handler: Callable[
        [ActionExecuteRequest], Awaitable[ActionExecuteResponse]
    ],
    now_utc_handler: Callable[[], datetime],
    auth_enabled_provider: Callable[[], bool],
    metrics_policy_update_roles_provider: Callable[[], set[str]],
    metrics_rollback_approver_roles_provider: Callable[[], set[str]],
    decompose_allow_synthetic_fallback_provider: Callable[[], bool],
    decompose_require_explicit_map_provider: Callable[[], bool],
    decompose_require_task_package_provider: Callable[[], bool],
    decompose_require_confirmation_provider: Callable[[], bool],
    workflow_scheduler_provider: Callable[[], WorkflowScheduler] | None = None,
    workflow_engine_provider: Callable[[], WorkflowEngine] | None = None,
) -> ControlCenterRuntimeBundle:
    dev_routing_matrix_service = DevRoutingMatrixService(
        bootstrap_config.dev_routing_matrix_file,
        logger=logger,
    )
    agent_rules_registry_service = AgentRulesRegistryService(
        bootstrap_config.agent_rules_registry_file,
        logger=logger,
    )

    state_store = (
        SQLiteStateStore(bootstrap_config.sqlite_path)
        if bootstrap_config.state_backend == "sqlite"
        else None
    )

    policy_holder: dict[str, object | None] = {"service": None}
    command_dispatch_service = CommandDispatchService(
        command_orchestration_policy_service_provider=lambda: (
            _must_have_service(
                policy_holder["service"],
                name="command_orchestration_policy_service",
            )
        ),
        agent_router_provider=lambda: agent_router,
        execute_action_handler=action_layer_execute_handler,
    )

    store = InMemoryOrchestrator(
        action_executor=command_dispatch_service.execute_command,
        state_store=state_store,
    )
    workflow_scheduler = WorkflowScheduler(state_store=state_store)
    workflow_agent_registry = AgentRegistry(
        mapping=agent_rules_registry_service.executor_mapping(
            scopes=("subproject", "main"),
        )
    )
    executor_service = ExecutorService(
        role_routing_policy_file=bootstrap_config.role_routing_policy_file,
        action_executor=action_layer_execute_handler,
        default_timeout_seconds=int(bootstrap_config.action_layer_timeout_seconds),
    )
    workflow_engine = WorkflowEngine(
        scheduler=workflow_scheduler,
        action_executor=command_dispatch_service.execute_workitem,
        executor_service=executor_service,
        agent_registry=workflow_agent_registry,
        max_module_reflows=bootstrap_config.max_module_reflows,
        release_requires_approval=bootstrap_config.release_approval_required,
    )
    resolved_workflow_scheduler_provider = (
        workflow_scheduler_provider
        if workflow_scheduler_provider is not None
        else lambda: workflow_scheduler
    )
    resolved_workflow_engine_provider = (
        workflow_engine_provider
        if workflow_engine_provider is not None
        else lambda: workflow_engine
    )

    def execute_action(request: ActionExecuteRequest) -> Awaitable[ActionExecuteResponse]:
        return action_layer_execute_handler(request)

    workflow_decompose_helpers_service = WorkflowDecomposeHelpersService()
    workflow_decompose_preview_support_service = WorkflowDecomposePreviewSupportService(
        normalize_module_candidates_handler=(
            workflow_decompose_helpers_service.normalize_module_candidates
        ),
        extract_modules_from_metadata_handler=(
            workflow_decompose_helpers_service.extract_modules_from_metadata
        ),
        validate_module_task_packages_handler=(
            workflow_decompose_helpers_service.validate_module_task_packages
        ),
        optional_text_handler=workflow_decompose_helpers_service.optional_text,
        now_utc_handler=now_utc_handler,
        persist_run_handler=lambda run_id: resolved_workflow_scheduler_provider().persist_run(
            run_id
        ),
    )
    workflow_execution_runtime_service = WorkflowExecutionRuntimeService(
        workflow_scheduler_provider=resolved_workflow_scheduler_provider,
        workflow_engine_provider=resolved_workflow_engine_provider,
        advance_decompose_bootstrap_run_loop_handler=lambda run_id, payload: (
            workflow_decompose_runtime_service.advance_decompose_bootstrap_run_loop(
                run_id,
                payload,
            )
        ),
        get_pending_decomposition=(
            workflow_decompose_preview_support_service.get_pending_decomposition
        ),
        get_pending_confirmation_status=(
            workflow_decompose_preview_support_service.get_pending_confirmation_status
        ),
    )
    workflow_decompose_support_service = WorkflowDecomposeSupportService(
        select_decomposition_for_preview_handler=(
            workflow_decompose_preview_support_service.select_decomposition_for_preview
        ),
        extract_preview_modules_handler=(
            workflow_decompose_preview_support_service.extract_preview_modules
        ),
        get_preview_snapshot_status_handler=(
            workflow_decompose_preview_support_service.get_preview_snapshot_status
        ),
        get_pending_decomposition_handler=(
            workflow_decompose_preview_support_service.get_pending_decomposition
        ),
        optional_text_handler=workflow_decompose_helpers_service.optional_text,
        normalize_text_list_handler=lambda value: normalize_text_list(value),
        list_workitems_handler=lambda run_id: resolved_workflow_scheduler_provider().list_workitems(
            run_id
        ),
        list_artifacts_handler=lambda run_id: resolved_workflow_scheduler_provider().list_artifacts(
            run_id
        ),
    )
    workflow_decompose_runtime_service = WorkflowDecomposeRuntimeService(
        workflow_scheduler_provider=resolved_workflow_scheduler_provider,
        workflow_engine_provider=resolved_workflow_engine_provider,
        now_utc_handler=now_utc_handler,
        optional_text_handler=workflow_decompose_helpers_service.optional_text,
        get_pending_decomposition_handler=(
            workflow_decompose_preview_support_service.get_pending_decomposition
        ),
        get_pending_confirmation_status_handler=(
            workflow_decompose_preview_support_service.get_pending_confirmation_status
        ),
        normalize_module_candidates_handler=(
            workflow_decompose_helpers_service.normalize_module_candidates
        ),
        get_preview_snapshot_status_handler=(
            workflow_decompose_preview_support_service.get_preview_snapshot_status
        ),
        build_decompose_aggregate_status_handler=(
            workflow_decompose_support_service.build_decompose_aggregate_status
        ),
        build_routing_decisions_response_handler=(
            workflow_decompose_support_service.build_routing_decisions_response
        ),
        get_or_build_decompose_bootstrap_preview_handler=(
            lambda run_id, run, refresh: workflow_decompose_preview_support_service.get_or_build_decompose_bootstrap_preview(
                run_id=run_id,
                run=run,
                refresh=refresh,
            )
        ),
        select_decomposition_for_preview_handler=(
            workflow_decompose_preview_support_service.select_decomposition_for_preview
        ),
        extract_preview_modules_handler=(
            workflow_decompose_preview_support_service.extract_preview_modules
        ),
        extract_module_task_packages_from_decomposition_handler=(
            workflow_decompose_preview_support_service.extract_module_task_packages_from_decomposition
        ),
        build_chief_decompose_prompt_handler=(
            workflow_decompose_helpers_service.build_chief_decompose_prompt
        ),
        execute_chief_action_handler=execute_action,
        build_synthetic_decomposition_fallback_handler=(
            workflow_decompose_helpers_service.build_synthetic_decomposition_fallback
        ),
        extract_modules_from_chief_response_handler=(
            workflow_decompose_helpers_service.extract_modules_from_chief_response
        ),
        validate_decomposition_coverage_handler=(
            workflow_decompose_helpers_service.validate_decomposition_coverage
        ),
        validate_requirement_module_mapping_handler=(
            workflow_decompose_helpers_service.validate_requirement_module_mapping
        ),
        validate_module_task_packages_handler=(
            workflow_decompose_helpers_service.validate_module_task_packages
        ),
        dev_routing_apply_handler=(
            lambda modules, module_task_packages, chief_metadata: dev_routing_matrix_service.apply(
                modules=modules,
                module_task_packages=module_task_packages,
                chief_metadata=chief_metadata,
            )
        ),
        decompose_allow_synthetic_fallback_provider=(
            decompose_allow_synthetic_fallback_provider
        ),
        decompose_require_explicit_map_provider=decompose_require_explicit_map_provider,
        decompose_require_task_package_provider=decompose_require_task_package_provider,
        decompose_require_confirmation_provider=decompose_require_confirmation_provider,
    )
    workflow_orchestration_support_service = WorkflowOrchestrationSupportService(
        select_decomposition_for_preview_handler=(
            workflow_decompose_preview_support_service.select_decomposition_for_preview
        ),
        extract_preview_modules_handler=(
            workflow_decompose_preview_support_service.extract_preview_modules
        ),
        get_pending_decomposition_handler=(
            workflow_decompose_preview_support_service.get_pending_decomposition
        ),
        optional_text_handler=workflow_decompose_helpers_service.optional_text,
        now_utc_handler=now_utc_handler,
        persist_run_handler=lambda run_id: resolved_workflow_scheduler_provider().persist_run(
            run_id
        ),
    )
    workflow_orchestration_runtime_service = WorkflowOrchestrationRuntimeService(
        workflow_scheduler_provider=resolved_workflow_scheduler_provider,
        now_utc_handler=now_utc_handler,
        optional_text_handler=workflow_decompose_helpers_service.optional_text,
        build_decompose_aggregate_status_handler=(
            workflow_decompose_support_service.build_decompose_aggregate_status
        ),
        build_orchestrate_decomposition_summary_handler=(
            workflow_orchestration_support_service.build_orchestrate_decomposition_summary
        ),
        build_orchestrate_decision_report_handler=(
            workflow_orchestration_support_service.build_orchestrate_decision_report
        ),
        build_orchestrate_telemetry_snapshot_handler=(
            workflow_orchestration_support_service.build_orchestrate_telemetry_snapshot
        ),
        read_orchestrate_latest_record_handler=(
            workflow_orchestration_support_service.read_orchestrate_latest_record
        ),
        persist_orchestrate_latest_record_handler=(
            workflow_orchestration_support_service.persist_orchestrate_latest_record
        ),
        resolve_orchestrate_recovery_action_handler=(
            workflow_orchestration_support_service.resolve_orchestrate_recovery_action
        ),
        get_pending_decomposition_handler=(
            workflow_decompose_preview_support_service.get_pending_decomposition
        ),
        get_pending_confirmation_status_handler=(
            workflow_decompose_preview_support_service.get_pending_confirmation_status
        ),
        decompose_bootstrap_workflow_run_handler=(
            workflow_decompose_runtime_service.decompose_bootstrap_workflow_run
        ),
        execute_workflow_run_handler=workflow_execution_runtime_service.execute_workflow_run,
        get_decompose_bootstrap_preview_handler=(
            workflow_decompose_runtime_service.get_decompose_bootstrap_preview
        ),
        confirm_decompose_bootstrap_workflow_run_handler=(
            workflow_decompose_runtime_service.confirm_decompose_bootstrap_workflow_run
        ),
        advance_decompose_bootstrap_run_loop_handler=(
            workflow_decompose_runtime_service.advance_decompose_bootstrap_run_loop
        ),
    )
    workflow_api_handlers_service = WorkflowAPIHandlersService(
        workflow_decompose_runtime_service_provider=(
            lambda: workflow_decompose_runtime_service
        ),
        workflow_orchestration_runtime_service_provider=(
            lambda: workflow_orchestration_runtime_service
        ),
        workflow_execution_runtime_service_provider=(
            lambda: workflow_execution_runtime_service
        ),
    )
    command_orchestration_policy_service = CommandOrchestrationPolicyService(
        enabled=bootstrap_config.command_orchestrate_policy_enabled,
        prefixes=bootstrap_config.command_orchestrate_prefixes,
        default_max_modules=bootstrap_config.command_orchestrate_default_max_modules,
        default_strategy=bootstrap_config.command_orchestrate_default_strategy,
        restart_canceled_policy=(
            bootstrap_config.command_orchestrate_restart_canceled_policy
        ),
        workflow_scheduler_provider=resolved_workflow_scheduler_provider,
        now_utc_handler=now_utc_handler,
        orchestrate_workflow_run_handler=(
            workflow_api_handlers_service.orchestrate_workflow_run
        ),
    )
    policy_holder["service"] = command_orchestration_policy_service

    metrics_alert_policy_store = MetricsAlertPolicyStore(
        bootstrap_config.metrics_alert_policy_file,
        bootstrap_config.metrics_alert_audit_file,
        bootstrap_config.metrics_rollback_approval_file,
        bootstrap_config.metrics_rollback_approval_purge_audit_file,
        rollback_approval_ttl_seconds=(
            bootstrap_config.metrics_rollback_approval_ttl_seconds
        ),
    )
    metrics_authorization_service = MetricsAuthorizationService(
        auth_enabled_provider=auth_enabled_provider,
        metrics_policy_update_roles_provider=metrics_policy_update_roles_provider,
        metrics_rollback_approver_roles_provider=(
            metrics_rollback_approver_roles_provider
        ),
    )
    return ControlCenterRuntimeBundle(
        state_store=state_store,
        store=store,
        workflow_scheduler=workflow_scheduler,
        workflow_engine=workflow_engine,
        command_dispatch_service=command_dispatch_service,
        workflow_api_handlers_service=workflow_api_handlers_service,
        command_orchestration_policy_service=command_orchestration_policy_service,
        agent_rules_registry_service=agent_rules_registry_service,
        metrics_alert_policy_store=metrics_alert_policy_store,
        metrics_authorization_service=metrics_authorization_service,
    )
