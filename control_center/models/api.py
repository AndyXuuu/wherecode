from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from control_center.models.hierarchy import CommandSource, CommandStatus
from control_center.models.v3_workflow import WorkflowRunStatus, WorkItem


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    assignee_agent: str = Field(default="auto-agent", min_length=1)


class CreateCommandRequest(BaseModel):
    text: str = Field(min_length=1)
    source: CommandSource = CommandSource.USER
    requested_by: str | None = None
    requires_approval: bool = False


class ApproveCommandRequest(BaseModel):
    approved_by: str = Field(min_length=1)


class CommandAcceptedResponse(BaseModel):
    command_id: str
    task_id: str
    project_id: str
    status: CommandStatus
    poll_url: str


class ActionLayerHealthResponse(BaseModel):
    status: str
    layer: str
    transport: str


class ActionExecuteRequest(BaseModel):
    text: str = Field(min_length=1)
    agent: str | None = Field(default=None, min_length=1)
    requested_by: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    role: str | None = Field(default=None, min_length=1)
    module_key: str | None = None


class DiscussionPrompt(BaseModel):
    question: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list, max_length=3)
    recommendation: str | None = None
    impact: str | None = None
    fingerprint: str | None = None


class ActionExecuteResponse(BaseModel):
    status: str
    summary: str
    agent: str
    trace_id: str
    metadata: dict[str, object] = Field(default_factory=dict)
    discussion: DiscussionPrompt | None = None


class MetricsWindowSummary(BaseModel):
    window_minutes: int
    total_commands: int
    success_count: int
    failed_count: int
    success_rate: float
    average_duration_ms: float


class RoutingRuleInfo(BaseModel):
    id: str
    agent: str
    priority: int
    enabled: bool
    keywords: list[str] = Field(default_factory=list)


class AgentRoutingConfigUpdateRequest(BaseModel):
    default_agent: str = Field(min_length=1)
    rules: list[RoutingRuleInfo] = Field(default_factory=list)


class AgentRoutingConfigResponse(BaseModel):
    default_agent: str
    rules: list[RoutingRuleInfo] = Field(default_factory=list)


class MetricsSummaryResponse(BaseModel):
    total_projects: int
    total_tasks: int
    total_commands: int
    in_flight_command_count: int
    waiting_approval_count: int
    success_count: int
    failed_count: int
    success_rate: float
    average_duration_ms: float
    executor_agent_counts: dict[str, int] = Field(default_factory=dict)
    routing_reason_counts: dict[str, int] = Field(default_factory=dict)
    routing_keyword_counts: dict[str, int] = Field(default_factory=dict)
    routing_rule_counts: dict[str, int] = Field(default_factory=dict)
    recent_windows: list[MetricsWindowSummary] = Field(default_factory=list)


class WorkflowMetricsResponse(BaseModel):
    total_runs: int
    run_status_counts: dict[str, int] = Field(default_factory=dict)
    total_workitems: int
    workitem_status_counts: dict[str, int] = Field(default_factory=dict)
    total_gate_checks: int
    gate_status_counts: dict[str, int] = Field(default_factory=dict)
    total_artifacts: int
    artifact_type_counts: dict[str, int] = Field(default_factory=dict)


class CreateWorkflowRunRequest(BaseModel):
    project_id: str = Field(min_length=1)
    task_id: str | None = None
    template_id: str | None = None
    requested_by: str | None = None
    summary: str | None = None


class CreateWorkItemRequest(BaseModel):
    role: str = Field(min_length=1)
    module_key: str | None = None
    assignee_agent: str = Field(default="auto-agent", min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    priority: int = Field(default=3, ge=1, le=5)
    requires_approval: bool = False
    discussion_budget: int = Field(default=2, ge=0)
    discussion_timeout_seconds: int = Field(default=120, ge=1)


class CompleteWorkItemRequest(BaseModel):
    success: bool


class ApproveWorkItemRequest(BaseModel):
    approved_by: str = Field(min_length=1)


class BootstrapWorkflowRequest(BaseModel):
    modules: list[str] = Field(min_length=1)


class DecomposeBootstrapWorkflowRequest(BaseModel):
    requirements: str = Field(min_length=1)
    max_modules: int = Field(default=6, ge=1, le=20)
    module_hints: list[str] = Field(default_factory=list)
    requested_by: str | None = None


class DecomposeBootstrapWorkflowResponse(BaseModel):
    run_id: str
    modules: list[str] = Field(default_factory=list)
    chief_summary: str
    chief_agent: str
    chief_trace_id: str
    chief_metadata: dict[str, object] = Field(default_factory=dict)
    workitems: list[WorkItem] = Field(default_factory=list)
    confirmation_required: bool = False
    confirmation_status: str | None = None
    confirmation_token: str | None = None


class ConfirmDecomposeBootstrapWorkflowRequest(BaseModel):
    confirmed_by: str = Field(min_length=1)
    approved: bool = True
    expected_modules: list[str] = Field(default_factory=list)
    confirmation_token: str | None = None
    reason: str | None = None


class ConfirmDecomposeBootstrapWorkflowResponse(BaseModel):
    run_id: str
    approved: bool
    confirmation_status: str
    confirmation_token: str | None = None
    confirmed_by: str
    reason: str | None = None
    modules: list[str] = Field(default_factory=list)
    workitems: list[WorkItem] = Field(default_factory=list)


class DecomposeBootstrapPendingWorkflowResponse(BaseModel):
    run_id: str
    has_pending_confirmation: bool = False
    confirmation_status: str | None = None
    confirmation_token: str | None = None
    requested_by: str | None = None
    requested_at: str | None = None
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    reason: str | None = None
    requirements: str | None = None
    module_hints: list[str] = Field(default_factory=list)
    max_modules: int | None = None
    modules: list[str] = Field(default_factory=list)
    chief_summary: str | None = None
    chief_agent: str | None = None
    chief_trace_id: str | None = None
    chief_metadata: dict[str, object] = Field(default_factory=dict)
    preview_ready: bool = False
    preview_stale: bool = False
    preview_generated_at: str | None = None
    preview_fingerprint: str | None = None


class DecomposeBootstrapAggregateStatusResponse(BaseModel):
    run_id: str
    run_status: WorkflowRunStatus
    decomposition_source: str = "none"
    has_decomposition: bool = False
    has_pending_confirmation: bool = False
    confirmation_status: str | None = None
    modules: list[str] = Field(default_factory=list)
    preview_ready: bool = False
    preview_stale: bool = False
    preview_generated_at: str | None = None
    preview_fingerprint: str | None = None
    workitem_total: int = 0
    workitem_status_counts: dict[str, int] = Field(default_factory=dict)
    module_workitem_counts: dict[str, int] = Field(default_factory=dict)
    global_workitem_count: int = 0
    bootstrap_started: bool = False
    bootstrap_finished: bool = False
    next_action: str | None = None


class DecomposeBootstrapAdvanceRequest(BaseModel):
    confirmed_by: str | None = None
    confirmation_token: str | None = None
    expected_modules: list[str] = Field(default_factory=list)
    max_loops: int = Field(default=20, ge=1, le=1000)
    force_refresh_preview: bool = False


class DecomposeBootstrapPreviewTask(BaseModel):
    task_key: str
    phase: str
    module_key: str
    role: str
    objective: str
    priority: int = Field(default=3, ge=1, le=5)
    deliverable: str | None = None
    depends_on_roles: list[str] = Field(default_factory=list)
    depends_on_task_keys: list[str] = Field(default_factory=list)
    level: int = Field(default=0, ge=0)


class DecomposeBootstrapPreviewResponse(BaseModel):
    run_id: str
    source: str
    generated_at: str | None = None
    cache_hit: bool = False
    cache_fingerprint: str | None = None
    modules: list[str] = Field(default_factory=list)
    task_count: int = 0
    terminal_task_keys: list[str] = Field(default_factory=list)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tasks: list[DecomposeBootstrapPreviewTask] = Field(default_factory=list)


class ExecuteWorkflowRunRequest(BaseModel):
    max_loops: int = Field(default=20, ge=1, le=1000)
    auto_advance_decompose: bool = True
    auto_advance_max_steps: int = Field(default=8, ge=1, le=100)
    auto_advance_execute_max_loops: int | None = Field(default=None, ge=1, le=1000)
    auto_advance_force_refresh_preview: bool = False
    decompose_confirmed_by: str | None = None
    decompose_confirmation_token: str | None = None
    decompose_expected_modules: list[str] = Field(default_factory=list)


class ExecuteWorkflowRunResponse(BaseModel):
    run_id: str
    run_status: WorkflowRunStatus
    executed_count: int
    failed_count: int
    remaining_ready_count: int
    remaining_pending_count: int
    waiting_discussion_count: int
    waiting_approval_count: int
    executed_workitem_ids: list[str] = Field(default_factory=list)
    failed_workitem_ids: list[str] = Field(default_factory=list)
    waiting_discussion_workitem_ids: list[str] = Field(default_factory=list)
    waiting_approval_workitem_ids: list[str] = Field(default_factory=list)
    decompose_auto_advance: DecomposeBootstrapAdvanceLoopResponse | None = None


class DecomposeBootstrapAdvanceResponse(BaseModel):
    run_id: str
    action_taken: str
    action_status: str
    reason: str | None = None
    status_before: DecomposeBootstrapAggregateStatusResponse
    status_after: DecomposeBootstrapAggregateStatusResponse
    preview: DecomposeBootstrapPreviewResponse | None = None
    confirmation: ConfirmDecomposeBootstrapWorkflowResponse | None = None
    execute: ExecuteWorkflowRunResponse | None = None


class DecomposeBootstrapAdvanceLoopRequest(BaseModel):
    confirmed_by: str | None = None
    confirmation_token: str | None = None
    expected_modules: list[str] = Field(default_factory=list)
    execute_max_loops: int = Field(default=20, ge=1, le=1000)
    force_refresh_preview: bool = False
    max_steps: int = Field(default=8, ge=1, le=100)
    stop_when_bootstrap_finished: bool = True


class DecomposeBootstrapAdvanceLoopResponse(BaseModel):
    run_id: str
    steps_executed: int = 0
    halted_reason: str
    last_action_taken: str | None = None
    action_taken_sequence: list[str] = Field(default_factory=list)
    action_status_counts: dict[str, int] = Field(default_factory=dict)
    final_status: DecomposeBootstrapAggregateStatusResponse
    steps: list[DecomposeBootstrapAdvanceResponse] = Field(default_factory=list)


class WorkflowRunOrchestrateDecomposePayload(BaseModel):
    requirements: str = Field(min_length=1)
    module_hints: list[str] = Field(default_factory=list)
    max_modules: int = Field(default=6, ge=1, le=20)
    requested_by: str | None = None


class WorkflowRunOrchestrateStrategy(str, Enum):
    SPEED = "speed"
    BALANCED = "balanced"
    SAFE = "safe"


class WorkflowRunOrchestrateRequest(BaseModel):
    strategy: WorkflowRunOrchestrateStrategy = WorkflowRunOrchestrateStrategy.SPEED
    requirements: str | None = None
    module_hints: list[str] = Field(default_factory=list)
    max_modules: int = Field(default=6, ge=1, le=20)
    requested_by: str | None = None
    decompose_payload: WorkflowRunOrchestrateDecomposePayload | None = None
    force_redecompose: bool = False
    execute: bool = True
    execute_max_loops: int = Field(default=20, ge=1, le=1000)
    auto_advance_decompose: bool = True
    auto_advance_max_steps: int = Field(default=8, ge=1, le=100)
    auto_advance_execute_max_loops: int | None = Field(default=None, ge=1, le=1000)
    auto_advance_force_refresh_preview: bool = False
    decompose_confirmed_by: str | None = None
    decompose_confirmation_token: str | None = None
    decompose_expected_modules: list[str] = Field(default_factory=list)


class WorkflowRunOrchestrateDecompositionSummary(BaseModel):
    source: str
    modules: list[str] = Field(default_factory=list)
    module_count: int = 0
    module_task_count: int = 0
    module_task_role_counts: dict[str, int] = Field(default_factory=dict)
    required_coverage_tags: list[str] = Field(default_factory=list)
    mapped_requirement_tag_count: int = 0
    requirement_points_count: int = 0
    confirmation_status: str | None = None
    has_pending_confirmation: bool = False
    preview_ready: bool = False
    preview_stale: bool = False
    preview_generated_at: str | None = None
    workitem_total: int = 0
    next_action: str | None = None


class WorkflowRunOrchestrateRecoveryActionScore(BaseModel):
    action: str
    priority: int = Field(default=50, ge=1, le=100)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str


class WorkflowRunOrchestrateExecutionProfile(BaseModel):
    auto_advance_decompose: bool = True
    execute_max_loops: int = Field(default=20, ge=1, le=1000)
    auto_advance_max_steps: int = Field(default=8, ge=1, le=100)
    auto_advance_execute_max_loops: int = Field(default=20, ge=1, le=1000)
    auto_advance_force_refresh_preview: bool = False


class WorkflowRunOrchestrateDecisionMachineReport(BaseModel):
    run_id: str
    strategy: WorkflowRunOrchestrateStrategy = WorkflowRunOrchestrateStrategy.SPEED
    orchestration_status: str
    reason: str | None = None
    actions: list[str] = Field(default_factory=list)
    next_action_before: str | None = None
    next_action_after: str | None = None
    decompose_triggered: bool = False
    execute_triggered: bool = False
    pending_confirmation_before: bool = False
    pending_confirmation_after: bool = False
    preview_ready_after: bool = False
    workitem_total_after: int = 0
    primary_recovery_action: str | None = None
    recovery_actions: list[str] = Field(default_factory=list)
    primary_recovery_priority: int | None = None
    primary_recovery_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    scored_recovery_actions: list[WorkflowRunOrchestrateRecoveryActionScore] = Field(
        default_factory=list
    )
    execution_profile: WorkflowRunOrchestrateExecutionProfile | None = None


class WorkflowRunOrchestrateDecisionReport(BaseModel):
    human_summary: str
    machine: WorkflowRunOrchestrateDecisionMachineReport


class WorkflowRunOrchestrateTelemetrySnapshot(BaseModel):
    started_at: datetime
    finished_at: datetime
    duration_ms: int = Field(default=0, ge=0)
    action_count: int = Field(default=0, ge=0)
    actions: list[str] = Field(default_factory=list)
    workitem_total_before: int = Field(default=0, ge=0)
    workitem_total_after: int = Field(default=0, ge=0)
    workitem_total_delta: int = 0
    unfinished_workitem_before: int = Field(default=0, ge=0)
    unfinished_workitem_after: int = Field(default=0, ge=0)
    unfinished_workitem_delta: int = 0
    pending_confirmation_before: bool = False
    pending_confirmation_after: bool = False
    pending_confirmation_cleared: bool = False
    preview_ready_before: bool = False
    preview_ready_after: bool = False
    preview_state_changed: bool = False
    next_action_before: str | None = None
    next_action_after: str | None = None
    next_action_changed: bool = False
    decompose_triggered: bool = False
    execute_triggered: bool = False
    execute_run_status: str | None = None
    execute_failed_count: int | None = Field(default=None, ge=0)
    execute_remaining_pending_count: int | None = Field(default=None, ge=0)


class WorkflowRunOrchestrateResponse(BaseModel):
    run_id: str
    strategy: WorkflowRunOrchestrateStrategy = WorkflowRunOrchestrateStrategy.SPEED
    orchestration_status: str
    reason: str | None = None
    actions: list[str] = Field(default_factory=list)
    status_before: DecomposeBootstrapAggregateStatusResponse
    status_after: DecomposeBootstrapAggregateStatusResponse
    decomposition_summary: WorkflowRunOrchestrateDecompositionSummary | None = None
    decision_report: WorkflowRunOrchestrateDecisionReport | None = None
    telemetry_snapshot: WorkflowRunOrchestrateTelemetrySnapshot | None = None
    decompose: DecomposeBootstrapWorkflowResponse | None = None
    execute: ExecuteWorkflowRunResponse | None = None


class WorkflowRunOrchestrateTelemetryRecord(BaseModel):
    run_id: str
    strategy: WorkflowRunOrchestrateStrategy = WorkflowRunOrchestrateStrategy.SPEED
    orchestration_status: str
    reason: str | None = None
    actions: list[str] = Field(default_factory=list)
    decision_report: WorkflowRunOrchestrateDecisionReport | None = None
    telemetry_snapshot: WorkflowRunOrchestrateTelemetrySnapshot
    recorded_at: datetime


class WorkflowRunOrchestrateLatestTelemetryResponse(BaseModel):
    run_id: str
    found: bool
    record: WorkflowRunOrchestrateTelemetryRecord | None = None


class WorkflowRunOrchestrateRecoveryExecuteRequest(BaseModel):
    action: str | None = None
    strategy: WorkflowRunOrchestrateStrategy = WorkflowRunOrchestrateStrategy.BALANCED
    requirements: str | None = None
    module_hints: list[str] = Field(default_factory=list)
    max_modules: int = Field(default=6, ge=1, le=20)
    requested_by: str | None = None
    execute: bool = True
    execute_max_loops: int = Field(default=20, ge=1, le=1000)
    auto_advance_decompose: bool = True
    auto_advance_max_steps: int = Field(default=8, ge=1, le=100)
    auto_advance_execute_max_loops: int | None = Field(default=None, ge=1, le=1000)
    auto_advance_force_refresh_preview: bool = False
    confirmed_by: str | None = None
    confirmation_token: str | None = None
    expected_modules: list[str] = Field(default_factory=list)
    advance_loop_max_steps: int = Field(default=8, ge=1, le=100)


class WorkflowRunOrchestrateRecoveryExecuteResponse(BaseModel):
    run_id: str
    action_source: str
    selected_action: str | None = None
    action_status: str
    reason: str | None = None
    latest_record_before: WorkflowRunOrchestrateTelemetryRecord | None = None
    orchestrate: WorkflowRunOrchestrateResponse | None = None
    preview: DecomposeBootstrapPreviewResponse | None = None
    confirmation: ConfirmDecomposeBootstrapWorkflowResponse | None = None
    advance_loop: DecomposeBootstrapAdvanceLoopResponse | None = None
    execute: ExecuteWorkflowRunResponse | None = None


class ResolveDiscussionRequest(BaseModel):
    decision: str = Field(min_length=1)
    resolved_by: str = Field(min_length=1)
    discussion_id: str | None = None


class MetricsAlertPolicy(BaseModel):
    failed_run_delta_gt: int = Field(default=0, ge=0)
    failed_run_count_gte: int = Field(default=1, ge=0)
    blocked_run_count_gte: int = Field(default=2, ge=0)
    waiting_approval_count_gte: int = Field(default=10, ge=0)
    in_flight_command_count_gte: int = Field(default=50, ge=0)


class MetricsAlertPolicyUpdateRequest(MetricsAlertPolicy):
    updated_by: str = Field(min_length=1)
    reason: str | None = None


class MetricsAlertPolicyResponse(MetricsAlertPolicy):
    policy_path: str
    updated_at: datetime
    audit_count: int = Field(default=0, ge=0)


class MetricsAlertPolicyAuditEntry(BaseModel):
    id: str
    updated_at: datetime
    updated_by: str
    reason: str | None = None
    rollback_from_audit_id: str | None = None
    rollback_request_id: str | None = None
    rollback_approval_id: str | None = None
    policy: MetricsAlertPolicy


class VerifyPolicyProfileConfig(BaseModel):
    allowed_resolvers: list[str] | None = None
    preflight_slo_min_pass_rate: float | None = Field(default=None, ge=0, le=1)
    preflight_slo_max_consecutive_failures: int | None = Field(default=None, ge=0)
    verify_slo_min_pass_rate: float | None = Field(default=None, ge=0, le=1)
    verify_slo_max_fetch_failures: int | None = Field(default=None, ge=0)


class VerifyPolicyRegistryResponse(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, VerifyPolicyProfileConfig] = Field(default_factory=dict)
    registry_path: str
    updated_at: datetime
    audit_count: int = Field(default=0, ge=0)


class VerifyPolicyRegistryUpdateRequest(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, VerifyPolicyProfileConfig] = Field(default_factory=dict)
    updated_by: str = Field(min_length=1)
    reason: str | None = None


class VerifyPolicyRegistryAuditEntry(BaseModel):
    id: str
    updated_at: datetime
    updated_by: str
    reason: str | None = None
    registry: dict[str, object]


class VerifyPolicyRegistryExportResponse(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, VerifyPolicyProfileConfig] = Field(default_factory=dict)
    generated_at: datetime
    source: str


class RollbackMetricsAlertPolicyRequest(BaseModel):
    audit_id: str = Field(min_length=1)
    updated_by: str = Field(min_length=1)
    reason: str | None = None
    dry_run: bool = False
    idempotency_key: str | None = None
    approval_id: str | None = None


class RollbackMetricsAlertPolicyResponse(BaseModel):
    source_audit_id: str
    dry_run: bool
    applied: bool
    idempotent_replay: bool = False
    policy: MetricsAlertPolicy
    policy_path: str
    audit_count: int = Field(default=0, ge=0)


class RollbackApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    USED = "used"
    EXPIRED = "expired"


class CreateRollbackApprovalRequest(BaseModel):
    audit_id: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    reason: str | None = None


class ApproveRollbackApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=1)


class RollbackApprovalResponse(BaseModel):
    id: str
    audit_id: str
    status: RollbackApprovalStatus
    requested_by: str
    approved_by: str | None = None
    used_by: str | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class RollbackApprovalStatsResponse(BaseModel):
    total: int = Field(default=0, ge=0)
    pending: int = Field(default=0, ge=0)
    approved: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    used: int = Field(default=0, ge=0)
    expired: int = Field(default=0, ge=0)


class PurgeRollbackApprovalsRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    remove_used: bool = True
    remove_expired: bool = True
    dry_run: bool = False
    older_than_seconds: int | None = Field(default=None, ge=0)


class PurgeRollbackApprovalsResponse(BaseModel):
    requested_by: str
    dry_run: bool
    remove_used: bool
    remove_expired: bool
    older_than_seconds: int | None = Field(default=None, ge=0)
    purge_audit_id: str | None = None
    removed_used: int = Field(default=0, ge=0)
    removed_expired: int = Field(default=0, ge=0)
    removed_total: int = Field(default=0, ge=0)
    remaining_total: int = Field(default=0, ge=0)


class PurgeRollbackApprovalsAuditEntry(BaseModel):
    id: str
    event_type: str = "approval_purge"
    requested_by: str
    dry_run: bool
    remove_used: bool | None = None
    remove_expired: bool | None = None
    older_than_seconds: int | None = Field(default=None, ge=0)
    keep_latest: int | None = Field(default=None, ge=0)
    removed_used: int = Field(default=0, ge=0)
    removed_expired: int = Field(default=0, ge=0)
    removed_total: int = Field(default=0, ge=0)
    remaining_total: int = Field(default=0, ge=0)
    created_at: datetime


class PurgeRollbackApprovalPurgeAuditsRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    dry_run: bool = False
    older_than_seconds: int | None = Field(default=None, ge=0)
    keep_latest: int = Field(default=0, ge=0)


class PurgeRollbackApprovalPurgeAuditsResponse(BaseModel):
    requested_by: str
    dry_run: bool
    older_than_seconds: int | None = Field(default=None, ge=0)
    keep_latest: int = Field(default=0, ge=0)
    purge_audit_gc_id: str | None = None
    removed_total: int = Field(default=0, ge=0)
    remaining_total: int = Field(default=0, ge=0)


class ExportRollbackApprovalPurgeAuditsResponse(BaseModel):
    exported_total: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1)
    event_type: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    generated_at: datetime
    checksum_scope: str = "entries"
    checksum_sha256: str
    entries: list[PurgeRollbackApprovalsAuditEntry] = Field(default_factory=list)
