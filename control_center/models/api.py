from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from control_center.models.hierarchy import CommandSource, CommandStatus
from control_center.models.v3_workflow import WorkflowRunStatus


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


class ExecuteWorkflowRunRequest(BaseModel):
    max_loops: int = Field(default=20, ge=1, le=1000)


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
