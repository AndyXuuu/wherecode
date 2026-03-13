from __future__ import annotations

from pydantic import BaseModel, Field

from control_center.models.hierarchy import CommandSource, CommandStatus


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


class AgentTraceStep(BaseModel):
    index: int = Field(default=1, ge=1)
    phase: str = ""
    content: str = ""
    tool: str = ""
    status: str = ""


class AgentExecutionTrace(BaseModel):
    standard: str = "ReAct"
    version: str = "1.0"
    loop_state: str = ""
    steps: list[AgentTraceStep] = Field(default_factory=list)
    final_decision: str = ""
    truncated: bool = False


class ActionExecuteResponse(BaseModel):
    status: str
    summary: str
    agent: str
    trace_id: str
    metadata: dict[str, object] = Field(default_factory=dict)
    discussion: DiscussionPrompt | None = None
    agent_trace: AgentExecutionTrace | None = None


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


class CommandOrchestratePolicyConfigResponse(BaseModel):
    enabled: bool
    prefixes: list[str] = Field(default_factory=list)
    default_max_modules: int = Field(ge=1, le=20)
    default_strategy: str
    restart_canceled_policy: str


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
