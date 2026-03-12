from datetime import datetime
from pathlib import Path
from typing import Any
import logging

from fastapi import FastAPI, HTTPException, status
from control_center.models import (
    ActionLayerHealthResponse,
    ApproveWorkItemRequest,
    BootstrapWorkflowRequest,
    DecomposeBootstrapWorkflowRequest,
    DecomposeBootstrapWorkflowResponse,
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapPendingWorkflowResponse,
    DecomposeBootstrapAggregateStatusResponse,
    WorkflowRunRoutingDecisionsResponse,
    DecomposeBootstrapAdvanceRequest,
    DecomposeBootstrapAdvanceResponse,
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    WorkflowRunOrchestrateDecomposePayload,
    WorkflowRunOrchestrateLatestTelemetryResponse,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateRecoveryExecuteResponse,
    WorkflowRunOrchestrateRequest,
    WorkflowRunOrchestrateResponse,
    DecomposeBootstrapPreviewResponse,
    CompleteWorkItemRequest,
    ExecuteWorkflowRunRequest,
    ExecuteWorkflowRunResponse,
    MetricsSummaryResponse,
    MetricsAlertPolicyAuditEntry,
    MetricsAlertPolicyResponse,
    MetricsAlertPolicyUpdateRequest,
    VerifyPolicyRegistryResponse,
    VerifyPolicyRegistryUpdateRequest,
    VerifyPolicyRegistryAuditEntry,
    VerifyPolicyRegistryExportResponse,
    CreateRollbackApprovalRequest,
    ApproveRollbackApprovalRequest,
    RollbackApprovalResponse,
    RollbackApprovalStatsResponse,
    PurgeRollbackApprovalsRequest,
    PurgeRollbackApprovalsResponse,
    PurgeRollbackApprovalsAuditEntry,
    PurgeRollbackApprovalPurgeAuditsRequest,
    PurgeRollbackApprovalPurgeAuditsResponse,
    ExportRollbackApprovalPurgeAuditsResponse,
    RollbackMetricsAlertPolicyRequest,
    RollbackMetricsAlertPolicyResponse,
    WorkflowMetricsResponse,
    ApproveCommandRequest,
    CommandAcceptedResponse,
    CreateCommandRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    CreateWorkflowRunRequest,
    CreateWorkItemRequest,
    Project,
    ProjectDetail,
    Artifact,
    GateCheck,
    WorkflowRun,
)
from control_center.services import (
    ActionLayerClient,
    AgentRouter,
    CommandDispatchService,
    CommandOrchestrationPolicyService,
    ContextMemoryStore,
    DevRoutingMatrixService,
    InMemoryOrchestrator,
    MetricsAuthorizationService,
    MetricsAlertPolicyStore,
    PolicyRollbackApprovalError,
    PolicyRollbackConflictError,
    WorkflowDecomposeHelpersService,
    WorkflowDecomposePreviewSupportService,
    WorkflowDecomposeSupportService,
    WorkflowAPIHandlersService,
    SQLiteStateStore,
    WorkflowDecomposeRuntimeService,
    WorkflowEngine,
    WorkflowExecutionRuntimeService,
    WorkflowOrchestrationRuntimeService,
    WorkflowOrchestrationSupportService,
    WorkflowScheduler,
    build_control_center_runtime,
    load_control_center_bootstrap_config,
    normalize_text_list,
)
from control_center.services.app_wiring import (
    build_ops_check_runtime,
    configure_control_center_middlewares,
    include_control_center_routers,
    resolve_allowed_origins,
)
from control_center.models.hierarchy import now_utc

app = FastAPI(title="WhereCode Control Center")
logger = logging.getLogger("wherecode.control_center")
bootstrap_config = load_control_center_bootstrap_config()
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=bootstrap_config.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
ACTION_LAYER_TIMEOUT_SECONDS = bootstrap_config.action_layer_timeout_seconds
action_layer = ActionLayerClient(
    base_url=bootstrap_config.action_layer_base_url,
    timeout_seconds=ACTION_LAYER_TIMEOUT_SECONDS,
)
agent_router = AgentRouter(bootstrap_config.agent_routing_file)
AUTH_ENABLED = bootstrap_config.auth_enabled
AUTH_TOKEN = bootstrap_config.auth_token
DECOMPOSE_REQUIRE_EXPLICIT_MAP = bootstrap_config.decompose_require_explicit_map
DECOMPOSE_REQUIRE_TASK_PACKAGE = bootstrap_config.decompose_require_task_package
DECOMPOSE_REQUIRE_CONFIRMATION = bootstrap_config.decompose_require_confirmation
DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK = bootstrap_config.decompose_allow_synthetic_fallback
METRICS_ALERT_POLICY_UPDATE_ROLES = bootstrap_config.metrics_alert_policy_update_roles
METRICS_ROLLBACK_REQUIRES_APPROVAL = bootstrap_config.metrics_rollback_requires_approval
METRICS_ROLLBACK_APPROVAL_TTL_SECONDS = (
    bootstrap_config.metrics_rollback_approval_ttl_seconds
)
METRICS_ROLLBACK_APPROVER_ROLES = bootstrap_config.metrics_rollback_approver_roles
AUTH_WHITELIST_PREFIXES = (
    "/healthz",
    "/docs",
    "/redoc",
    "/openapi.json",
)
COMMAND_ORCHESTRATE_POLICY_ENABLED = bootstrap_config.command_orchestrate_policy_enabled
COMMAND_ORCHESTRATE_PREFIXES = bootstrap_config.command_orchestrate_prefixes
COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES = (
    bootstrap_config.command_orchestrate_default_max_modules
)
COMMAND_ORCHESTRATE_DEFAULT_STRATEGY = (
    bootstrap_config.command_orchestrate_default_strategy
)
COMMAND_ORCHESTRATE_RESTART_CANCELED_POLICY = (
    bootstrap_config.command_orchestrate_restart_canceled_policy
)
DEV_ROUTING_MATRIX_FILE = bootstrap_config.dev_routing_matrix_file
runtime_bundle = build_control_center_runtime(
    bootstrap_config=bootstrap_config,
    logger=logger,
    agent_router=agent_router,
    action_layer_execute_handler=lambda payload: action_layer.execute(payload),
    now_utc_handler=lambda: now_utc(),
    auth_enabled_provider=lambda: AUTH_ENABLED,
    metrics_policy_update_roles_provider=lambda: METRICS_ALERT_POLICY_UPDATE_ROLES,
    metrics_rollback_approver_roles_provider=lambda: METRICS_ROLLBACK_APPROVER_ROLES,
    decompose_allow_synthetic_fallback_provider=lambda: DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK,
    decompose_require_explicit_map_provider=lambda: DECOMPOSE_REQUIRE_EXPLICIT_MAP,
    decompose_require_task_package_provider=lambda: DECOMPOSE_REQUIRE_TASK_PACKAGE,
    decompose_require_confirmation_provider=lambda: DECOMPOSE_REQUIRE_CONFIRMATION,
    workflow_scheduler_provider=lambda: workflow_scheduler,
    workflow_engine_provider=lambda: workflow_engine,
)
state_store = runtime_bundle.state_store
store = runtime_bundle.store
workflow_scheduler = runtime_bundle.workflow_scheduler
workflow_engine = runtime_bundle.workflow_engine
command_dispatch_service = runtime_bundle.command_dispatch_service
workflow_api_handlers_service = runtime_bundle.workflow_api_handlers_service
command_orchestration_policy_service = (
    runtime_bundle.command_orchestration_policy_service
)
agent_rules_registry_service = runtime_bundle.agent_rules_registry_service
metrics_alert_policy_store = runtime_bundle.metrics_alert_policy_store
metrics_authorization_service = runtime_bundle.metrics_authorization_service
context_memory_store = ContextMemoryStore(state_store=state_store)

control_center_root = Path(__file__).resolve().parents[1]
ops_check_runtime = build_ops_check_runtime(
    state_store=state_store,
    root_dir=control_center_root,
)
configure_control_center_middlewares(
    app,
    allowed_origins=resolve_allowed_origins(bootstrap_config.allowed_origins_raw),
    logger=logger,
    auth_enabled_provider=lambda: AUTH_ENABLED,
    auth_token_provider=lambda: AUTH_TOKEN,
    auth_whitelist_prefixes=AUTH_WHITELIST_PREFIXES,
    extract_request_token=metrics_authorization_service.extract_request_token,
)
include_control_center_routers(
    app,
    store_provider=lambda: store,
    command_orchestrate_policy_config_provider=lambda: {
        "enabled": COMMAND_ORCHESTRATE_POLICY_ENABLED,
        "prefixes": list(COMMAND_ORCHESTRATE_PREFIXES),
        "default_max_modules": COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES,
        "default_strategy": COMMAND_ORCHESTRATE_DEFAULT_STRATEGY,
        "restart_canceled_policy": COMMAND_ORCHESTRATE_RESTART_CANCELED_POLICY,
    },
    context_memory_store_provider=lambda: context_memory_store,
    agent_rules_registry_provider=lambda: agent_rules_registry_service,
    workflow_scheduler_provider=lambda: workflow_scheduler,
    workflow_engine_provider=lambda: workflow_engine,
    metrics_alert_policy_store_provider=lambda: metrics_alert_policy_store,
    authorize_metrics_policy_update=(
        metrics_authorization_service.authorize_metrics_policy_update
    ),
    authorize_metrics_rollback_approval=(
        metrics_authorization_service.authorize_metrics_rollback_approval
    ),
    metrics_rollback_requires_approval_provider=lambda: METRICS_ROLLBACK_REQUIRES_APPROVAL,
    agent_router_provider=lambda: agent_router,
    action_layer_health_handler=lambda: action_layer.get_health(),
    action_layer_execute_handler=lambda payload: action_layer.execute(payload),
    execute_workflow_run_handler=workflow_api_handlers_service.execute_workflow_run,
    interrupt_workflow_run_handler=workflow_api_handlers_service.interrupt_workflow_run,
    decompose_bootstrap_handler=(
        workflow_api_handlers_service.decompose_bootstrap_workflow_run
    ),
    decompose_pending_handler=workflow_api_handlers_service.get_decompose_bootstrap_pending,
    decompose_status_handler=(
        workflow_api_handlers_service.get_decompose_bootstrap_aggregate_status
    ),
    routing_decisions_handler=(
        workflow_api_handlers_service.get_workflow_run_routing_decisions
    ),
    decompose_preview_handler=workflow_api_handlers_service.get_decompose_bootstrap_preview,
    decompose_advance_handler=workflow_api_handlers_service.advance_decompose_bootstrap_run,
    decompose_advance_loop_handler=(
        workflow_api_handlers_service.advance_decompose_bootstrap_run_loop
    ),
    decompose_confirm_handler=(
        workflow_api_handlers_service.confirm_decompose_bootstrap_workflow_run
    ),
    orchestrate_handler=workflow_api_handlers_service.orchestrate_workflow_run,
    orchestrate_latest_handler=workflow_api_handlers_service.get_latest_orchestrate_telemetry,
    orchestrate_recover_handler=(
        workflow_api_handlers_service.execute_orchestrate_recovery_action
    ),
    ops_check_runtime=ops_check_runtime,
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "transport": "http-async"}
