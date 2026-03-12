from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from control_center.models.v3_workflow import WorkflowRunStatus, WorkItem


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


class WorkflowRunRoutingDecision(BaseModel):
    module_key: str
    rule_id: str | None = None
    target_role: str | None = None
    capability_id: str | None = None
    executor: str | None = None
    required_checks: list[str] = Field(default_factory=list)
    handoff_roles: list[str] = Field(default_factory=list)
    requires_human_confirmation: bool = False
    signals: dict[str, list[str]] = Field(default_factory=dict)


class WorkflowRunRoutingDecisionsResponse(BaseModel):
    run_id: str
    source: str = "none"
    confirmation_status: str | None = None
    has_routing_decisions: bool = False
    module_count: int = 0
    decisions: list[WorkflowRunRoutingDecision] = Field(default_factory=list)


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


class InterruptWorkflowRunRequest(BaseModel):
    requested_by: str | None = None
    reason: str | None = None
    skip_non_terminal_workitems: bool = True


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


class InterruptWorkflowRunResponse(BaseModel):
    run_id: str
    previous_status: WorkflowRunStatus
    run_status: WorkflowRunStatus
    interrupt_applied: bool = False
    skipped_workitem_ids: list[str] = Field(default_factory=list)
    reason: str | None = None


class RestartWorkflowRunRequest(BaseModel):
    requested_by: str | None = None
    reason: str | None = None
    copy_decomposition: bool = True


class RestartWorkflowRunResponse(BaseModel):
    source_run_id: str
    restarted_run_id: str
    restarted_run_status: WorkflowRunStatus
    copied_decomposition: bool = False


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
    restarted_run_id: str | None = None
    restarted_run_status: WorkflowRunStatus | None = None
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
