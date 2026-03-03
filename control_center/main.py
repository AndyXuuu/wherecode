import os
import time
import json
import hashlib
from datetime import datetime
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionLayerHealthResponse,
    AgentRoutingConfigResponse,
    AgentRoutingConfigUpdateRequest,
    ApproveWorkItemRequest,
    BootstrapWorkflowRequest,
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
    Command,
    CommandAcceptedResponse,
    CreateCommandRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    CreateWorkflowRunRequest,
    CreateWorkItemRequest,
    Project,
    ProjectDetail,
    ResolveDiscussionRequest,
    Task,
    DiscussionSession,
    Artifact,
    GateCheck,
    WorkflowRun,
    WorkItem,
)
from control_center.services import (
    ActionLayerClient,
    ActionLayerClientError,
    AgentRouter,
    InMemoryOrchestrator,
    MetricsAlertPolicyStore,
    PolicyRollbackApprovalError,
    PolicyRollbackConflictError,
    SQLiteStateStore,
    WorkflowEngine,
    WorkflowScheduler,
)
from control_center.models.hierarchy import now_utc

app = FastAPI(title="WhereCode Control Center")
logger = logging.getLogger("wherecode.control_center")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("WHERECODE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
action_layer = ActionLayerClient(
    base_url=os.getenv("ACTION_LAYER_BASE_URL", "http://127.0.0.1:8100")
)
agent_router = AgentRouter(
    os.getenv("WHERECODE_AGENT_ROUTING_FILE", "control_center/agents.routing.json")
)
AUTH_ENABLED = os.getenv("WHERECODE_AUTH_ENABLED", "true").lower() == "true"
AUTH_TOKEN = os.getenv("WHERECODE_TOKEN", "change-me")
METRICS_ALERT_POLICY_UPDATE_ROLES = {
    role.strip().lower()
    for role in os.getenv(
        "WHERECODE_METRICS_ALERT_POLICY_UPDATE_ROLES",
        "ops-admin,chief-architect,release-manager",
    ).split(",")
    if role.strip()
}
METRICS_ROLLBACK_REQUIRES_APPROVAL = (
    os.getenv("WHERECODE_METRICS_ROLLBACK_REQUIRES_APPROVAL", "false").lower() == "true"
)
try:
    METRICS_ROLLBACK_APPROVAL_TTL_SECONDS = int(
        os.getenv("WHERECODE_METRICS_ROLLBACK_APPROVAL_TTL_SECONDS", "86400")
    )
except ValueError:
    METRICS_ROLLBACK_APPROVAL_TTL_SECONDS = 86400
METRICS_ROLLBACK_APPROVER_ROLES = {
    role.strip().lower()
    for role in os.getenv(
        "WHERECODE_METRICS_ROLLBACK_APPROVER_ROLES",
        "ops-admin,release-manager,chief-architect",
    ).split(",")
    if role.strip()
}
AUTH_WHITELIST_PREFIXES = (
    "/healthz",
    "/docs",
    "/redoc",
    "/openapi.json",
)


async def execute_with_action_layer(command: Command, task: Task) -> ActionExecuteResponse:
    routing = agent_router.route(task.assignee_agent, command.text)
    command.metadata["routed_agent"] = routing.agent
    command.metadata["routing_reason"] = routing.reason
    if routing.matched_keyword is not None:
        command.metadata["routing_keyword"] = routing.matched_keyword
    else:
        command.metadata.pop("routing_keyword", None)
    if routing.rule_id is not None:
        command.metadata["routing_rule_id"] = routing.rule_id
    else:
        command.metadata.pop("routing_rule_id", None)
    return await action_layer.execute(
        ActionExecuteRequest(
            text=command.text,
            agent=routing.agent,
            requested_by=command.requested_by,
            task_id=command.task_id,
            project_id=command.project_id,
        )
    )


async def execute_workitem_with_action_layer(
    request: ActionExecuteRequest,
) -> ActionExecuteResponse:
    return await action_layer.execute(request)


state_backend = os.getenv("WHERECODE_STATE_BACKEND", "memory").lower()
sqlite_path = os.getenv("WHERECODE_SQLITE_PATH", ".wherecode/state.db")
state_store = SQLiteStateStore(sqlite_path) if state_backend == "sqlite" else None
store = InMemoryOrchestrator(
    action_executor=execute_with_action_layer,
    state_store=state_store,
)
workflow_scheduler = WorkflowScheduler(state_store=state_store)
workflow_engine = WorkflowEngine(
    scheduler=workflow_scheduler,
    action_executor=execute_workitem_with_action_layer,
    max_module_reflows=int(os.getenv("WHERECODE_MAX_MODULE_REFLOWS", "1")),
    release_requires_approval=(
        os.getenv("WHERECODE_RELEASE_APPROVAL_REQUIRED", "false").lower() == "true"
    ),
)
metrics_alert_policy_store = MetricsAlertPolicyStore(
    os.getenv("WHERECODE_METRICS_ALERT_POLICY_FILE", "control_center/metrics_alert_policy.json"),
    os.getenv("WHERECODE_METRICS_ALERT_AUDIT_FILE", ".wherecode/metrics_alert_policy_audit.jsonl"),
    os.getenv(
        "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE",
        ".wherecode/metrics_rollback_approvals.jsonl",
    ),
    os.getenv(
        "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE",
        ".wherecode/metrics_rollback_approval_purge_audit.jsonl",
    ),
    rollback_approval_ttl_seconds=METRICS_ROLLBACK_APPROVAL_TTL_SECONDS,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("WHERECODE_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_request_token(request: Request) -> str | None:
    bearer = request.headers.get("Authorization", "")
    if bearer.startswith("Bearer "):
        return bearer[7:].strip()
    header_token = request.headers.get("X-WhereCode-Token")
    if header_token:
        return header_token.strip()
    return None


def _extract_request_role(request: Request) -> str | None:
    role = request.headers.get("X-WhereCode-Role")
    if role:
        return role.strip().lower()
    return None


def _authorize_metrics_policy_update(request: Request, *, updated_by: str) -> str:
    normalized_updated_by = updated_by.strip().lower()
    if not AUTH_ENABLED:
        return normalized_updated_by

    role = _extract_request_role(request)
    if not role:
        raise HTTPException(
            status_code=403,
            detail="missing role header: X-WhereCode-Role",
        )
    if role not in METRICS_ALERT_POLICY_UPDATE_ROLES:
        raise HTTPException(status_code=403, detail=f"role not allowed: {role}")
    if normalized_updated_by != role:
        raise HTTPException(
            status_code=409,
            detail="updated_by must match authenticated role",
        )
    return role


def _authorize_metrics_rollback_approval(request: Request, *, approved_by: str) -> str:
    normalized_approved_by = approved_by.strip().lower()
    if not AUTH_ENABLED:
        return normalized_approved_by

    role = _extract_request_role(request)
    if not role:
        raise HTTPException(
            status_code=403,
            detail="missing role header: X-WhereCode-Role",
        )
    if role not in METRICS_ROLLBACK_APPROVER_ROLES:
        raise HTTPException(status_code=403, detail=f"role not allowed: {role}")
    if normalized_approved_by != role:
        raise HTTPException(
            status_code=409,
            detail="approved_by must match authenticated role",
        )
    return role


def _build_routing_config_response() -> AgentRoutingConfigResponse:
    config = agent_router.get_config()
    return AgentRoutingConfigResponse(
        default_agent=str(config["default_agent"]),
        rules=[
            {
                "id": str(item["id"]),
                "agent": str(item["agent"]),
                "priority": int(item["priority"]),
                "enabled": bool(item["enabled"]),
                "keywords": list(item["keywords"]),
            }
            for item in config["rules"]
            if isinstance(item, dict)
        ],
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = f"req_{uuid4().hex[:12]}"
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not AUTH_ENABLED:
        return await call_next(request)

    if request.url.path.startswith(AUTH_WHITELIST_PREFIXES):
        return await call_next(request)

    token = _extract_request_token(request)
    if not token or token != AUTH_TOKEN:
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})

    return await call_next(request)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "transport": "http-async"}


@app.get("/action-layer/health", response_model=ActionLayerHealthResponse)
async def action_layer_health() -> ActionLayerHealthResponse:
    try:
        return await action_layer.get_health()
    except ActionLayerClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/action-layer/execute", response_model=ActionExecuteResponse)
async def action_layer_execute(payload: ActionExecuteRequest) -> ActionExecuteResponse:
    try:
        return await action_layer.execute(payload)
    except ActionLayerClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(payload: CreateProjectRequest) -> Project:
    return await store.create_project(payload)


@app.get("/projects", response_model=list[Project])
async def list_projects() -> list[Project]:
    return await store.list_projects()


@app.post(
    "/projects/{project_id}/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(project_id: str, payload: CreateTaskRequest) -> Task:
    return await store.create_task(project_id, payload)


@app.get("/projects/{project_id}/tasks", response_model=list[Task])
async def list_tasks(project_id: str) -> list[Task]:
    return await store.list_tasks(project_id)


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str) -> Task:
    return await store.get_task(task_id)


@app.post(
    "/tasks/{task_id}/commands",
    response_model=CommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_command(task_id: str, payload: CreateCommandRequest) -> CommandAcceptedResponse:
    command = await store.create_command(task_id, payload)
    return CommandAcceptedResponse(
        command_id=command.id,
        task_id=command.task_id,
        project_id=command.project_id,
        status=command.status,
        poll_url=f"/commands/{command.id}",
    )


@app.get("/tasks/{task_id}/commands", response_model=list[Command])
async def list_commands(task_id: str) -> list[Command]:
    return await store.list_commands(task_id)


@app.get("/commands/{command_id}", response_model=Command)
async def get_command(command_id: str) -> Command:
    return await store.get_command(command_id)


@app.post("/commands/{command_id}/approve", response_model=Command)
async def approve_command(command_id: str, payload: ApproveCommandRequest) -> Command:
    return await store.approve_command(command_id, payload.approved_by)


@app.get("/projects/{project_id}/snapshot", response_model=ProjectDetail)
async def get_project_snapshot(project_id: str) -> ProjectDetail:
    return await store.get_project_detail(project_id)


@app.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary() -> MetricsSummaryResponse:
    return await store.get_metrics_summary()


@app.get("/metrics/workflows", response_model=WorkflowMetricsResponse)
async def get_workflow_metrics() -> WorkflowMetricsResponse:
    payload = workflow_scheduler.get_metrics()
    return WorkflowMetricsResponse(**payload)


@app.get(
    "/metrics/workflows/alert-policy",
    response_model=MetricsAlertPolicyResponse,
)
async def get_metrics_alert_policy() -> MetricsAlertPolicyResponse:
    payload = metrics_alert_policy_store.get_policy()
    return MetricsAlertPolicyResponse(**payload)


@app.put(
    "/metrics/workflows/alert-policy",
    response_model=MetricsAlertPolicyResponse,
)
async def update_metrics_alert_policy(
    request: Request,
    payload: MetricsAlertPolicyUpdateRequest,
) -> MetricsAlertPolicyResponse:
    actor = _authorize_metrics_policy_update(
        request,
        updated_by=payload.updated_by,
    )
    updated = metrics_alert_policy_store.update_policy(
        {
            "failed_run_delta_gt": payload.failed_run_delta_gt,
            "failed_run_count_gte": payload.failed_run_count_gte,
            "blocked_run_count_gte": payload.blocked_run_count_gte,
            "waiting_approval_count_gte": payload.waiting_approval_count_gte,
            "in_flight_command_count_gte": payload.in_flight_command_count_gte,
        },
        updated_by=actor,
        reason=payload.reason,
    )
    return MetricsAlertPolicyResponse(**updated)


@app.get(
    "/metrics/workflows/alert-policy/verify-policy",
    response_model=VerifyPolicyRegistryResponse,
)
async def get_metrics_verify_policy_registry() -> VerifyPolicyRegistryResponse:
    payload = metrics_alert_policy_store.get_verify_policy_registry()
    return VerifyPolicyRegistryResponse(**payload)


@app.put(
    "/metrics/workflows/alert-policy/verify-policy",
    response_model=VerifyPolicyRegistryResponse,
)
async def update_metrics_verify_policy_registry(
    request: Request,
    payload: VerifyPolicyRegistryUpdateRequest,
) -> VerifyPolicyRegistryResponse:
    actor = _authorize_metrics_policy_update(
        request,
        updated_by=payload.updated_by,
    )
    try:
        updated = metrics_alert_policy_store.update_verify_policy_registry(
            {
                "default_profile": payload.default_profile,
                "profiles": {
                    key: value.model_dump(exclude_none=True)
                    for key, value in payload.profiles.items()
                },
            },
            updated_by=actor,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VerifyPolicyRegistryResponse(**updated)


@app.get(
    "/metrics/workflows/alert-policy/verify-policy/audits",
    response_model=list[VerifyPolicyRegistryAuditEntry],
)
async def list_metrics_verify_policy_registry_audits(
    limit: int = 20,
) -> list[VerifyPolicyRegistryAuditEntry]:
    entries = metrics_alert_policy_store.list_verify_policy_registry_audits(limit=limit)
    return [VerifyPolicyRegistryAuditEntry(**item) for item in entries]


@app.get(
    "/metrics/workflows/alert-policy/verify-policy/export",
    response_model=VerifyPolicyRegistryExportResponse,
)
async def export_metrics_verify_policy_registry() -> VerifyPolicyRegistryExportResponse:
    payload = metrics_alert_policy_store.export_verify_policy_registry()
    return VerifyPolicyRegistryExportResponse(**payload)


@app.post(
    "/metrics/workflows/alert-policy/rollback-approvals",
    response_model=RollbackApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_metrics_rollback_approval(
    request: Request,
    payload: CreateRollbackApprovalRequest,
) -> RollbackApprovalResponse:
    actor = _authorize_metrics_policy_update(request, updated_by=payload.requested_by)
    try:
        created = metrics_alert_policy_store.create_rollback_approval(
            audit_id=payload.audit_id,
            requested_by=actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RollbackApprovalResponse(**created)


@app.get(
    "/metrics/workflows/alert-policy/rollback-approvals",
    response_model=list[RollbackApprovalResponse],
)
async def list_metrics_rollback_approvals(
    limit: int = 20,
    status_filter: str | None = None,
) -> list[RollbackApprovalResponse]:
    entries = metrics_alert_policy_store.list_rollback_approvals(
        limit=limit,
        status=status_filter,
    )
    return [RollbackApprovalResponse(**item) for item in entries]


@app.get(
    "/metrics/workflows/alert-policy/rollback-approvals/stats",
    response_model=RollbackApprovalStatsResponse,
)
async def get_metrics_rollback_approval_stats() -> RollbackApprovalStatsResponse:
    payload = metrics_alert_policy_store.get_rollback_approval_stats()
    return RollbackApprovalStatsResponse(**payload)


@app.post(
    "/metrics/workflows/alert-policy/rollback-approvals/purge",
    response_model=PurgeRollbackApprovalsResponse,
)
async def purge_metrics_rollback_approvals(
    request: Request,
    payload: PurgeRollbackApprovalsRequest,
) -> PurgeRollbackApprovalsResponse:
    actor = _authorize_metrics_policy_update(request, updated_by=payload.requested_by)
    result = metrics_alert_policy_store.purge_rollback_approvals(
        remove_used=payload.remove_used,
        remove_expired=payload.remove_expired,
        dry_run=payload.dry_run,
        older_than_seconds=payload.older_than_seconds,
        requested_by=actor,
    )
    return PurgeRollbackApprovalsResponse(
        requested_by=actor,
        dry_run=payload.dry_run,
        remove_used=payload.remove_used,
        remove_expired=payload.remove_expired,
        older_than_seconds=payload.older_than_seconds,
        **result,
    )


@app.get(
    "/metrics/workflows/alert-policy/rollback-approvals/purge-audits",
    response_model=list[PurgeRollbackApprovalsAuditEntry],
)
async def list_metrics_rollback_approval_purge_audits(
    limit: int = 20,
) -> list[PurgeRollbackApprovalsAuditEntry]:
    entries = metrics_alert_policy_store.list_rollback_approval_purge_audits(limit=limit)
    return [PurgeRollbackApprovalsAuditEntry(**item) for item in entries]


@app.get(
    "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/export",
    response_model=ExportRollbackApprovalPurgeAuditsResponse,
)
async def export_metrics_rollback_approval_purge_audits(
    limit: int = 100,
    event_type: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> ExportRollbackApprovalPurgeAuditsResponse:
    normalized_limit = max(1, min(limit, 5000))
    entries = metrics_alert_policy_store.list_rollback_approval_purge_audits(
        limit=normalized_limit,
        event_type=event_type,
        created_after=created_after,
        created_before=created_before,
    )
    normalized_entries = [PurgeRollbackApprovalsAuditEntry(**item) for item in entries]
    digest_payload = [
        item.model_dump(mode="json")
        for item in normalized_entries
    ]
    checksum_sha256 = hashlib.sha256(
        json.dumps(digest_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return ExportRollbackApprovalPurgeAuditsResponse(
        exported_total=len(normalized_entries),
        limit=normalized_limit,
        event_type=event_type.strip() if event_type else None,
        created_after=created_after,
        created_before=created_before,
        generated_at=now_utc(),
        checksum_scope="entries",
        checksum_sha256=checksum_sha256,
        entries=normalized_entries,
    )


@app.post(
    "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
    response_model=PurgeRollbackApprovalPurgeAuditsResponse,
)
async def purge_metrics_rollback_approval_purge_audits(
    request: Request,
    payload: PurgeRollbackApprovalPurgeAuditsRequest,
) -> PurgeRollbackApprovalPurgeAuditsResponse:
    actor = _authorize_metrics_policy_update(request, updated_by=payload.requested_by)
    if payload.older_than_seconds is None and payload.keep_latest == 0:
        raise HTTPException(
            status_code=409,
            detail="safety check failed: provide older_than_seconds or keep_latest",
        )
    result = metrics_alert_policy_store.purge_rollback_approval_purge_audits(
        dry_run=payload.dry_run,
        older_than_seconds=payload.older_than_seconds,
        keep_latest=payload.keep_latest,
        requested_by=actor,
    )
    return PurgeRollbackApprovalPurgeAuditsResponse(
        requested_by=actor,
        dry_run=payload.dry_run,
        older_than_seconds=payload.older_than_seconds,
        keep_latest=payload.keep_latest,
        **result,
    )


@app.post(
    "/metrics/workflows/alert-policy/rollback-approvals/{approval_id}/approve",
    response_model=RollbackApprovalResponse,
)
async def approve_metrics_rollback_approval(
    approval_id: str,
    request: Request,
    payload: ApproveRollbackApprovalRequest,
) -> RollbackApprovalResponse:
    actor = _authorize_metrics_rollback_approval(
        request,
        approved_by=payload.approved_by,
    )
    try:
        approved = metrics_alert_policy_store.approve_rollback_approval(
            approval_id,
            approved_by=actor,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PolicyRollbackApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RollbackApprovalResponse(**approved)


@app.post(
    "/metrics/workflows/alert-policy/rollback",
    response_model=RollbackMetricsAlertPolicyResponse,
)
async def rollback_metrics_alert_policy(
    request: Request,
    payload: RollbackMetricsAlertPolicyRequest,
) -> RollbackMetricsAlertPolicyResponse:
    actor = _authorize_metrics_policy_update(
        request,
        updated_by=payload.updated_by,
    )
    if METRICS_ROLLBACK_REQUIRES_APPROVAL and not payload.dry_run:
        approval_id = (payload.approval_id or "").strip()
        if not approval_id:
            raise HTTPException(
                status_code=409,
                detail="rollback approval required: approval_id is missing",
            )
    else:
        approval_id = (payload.approval_id or "").strip() or None
    try:
        rolled = metrics_alert_policy_store.rollback_to_audit(
            payload.audit_id,
            updated_by=actor,
            reason=payload.reason,
            dry_run=payload.dry_run,
            idempotency_key=payload.idempotency_key,
            approval_id=approval_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PolicyRollbackApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PolicyRollbackConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RollbackMetricsAlertPolicyResponse(**rolled)


@app.get(
    "/metrics/workflows/alert-policy/audits",
    response_model=list[MetricsAlertPolicyAuditEntry],
)
async def list_metrics_alert_policy_audits(limit: int = 20) -> list[MetricsAlertPolicyAuditEntry]:
    entries = metrics_alert_policy_store.list_audits(limit=limit)
    normalized: list[MetricsAlertPolicyAuditEntry] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        updated_at = item.get("updated_at")
        if updated_at is None:
            continue
        policy = item.get("policy")
        if not isinstance(policy, dict):
            policy = {}
        entry_id = str(item.get("id", "")).strip()
        if not entry_id:
            continue
        normalized.append(
            MetricsAlertPolicyAuditEntry(
                id=entry_id,
                updated_at=updated_at,
                updated_by=str(item.get("updated_by", "")).strip(),
                reason=str(item["reason"]) if item.get("reason") is not None else None,
                rollback_from_audit_id=(
                    str(item["rollback_from_audit_id"])
                    if item.get("rollback_from_audit_id") is not None
                    else None
                ),
                rollback_request_id=(
                    str(item["rollback_request_id"])
                    if item.get("rollback_request_id") is not None
                    else None
                ),
                rollback_approval_id=(
                    str(item["rollback_approval_id"])
                    if item.get("rollback_approval_id") is not None
                    else None
                ),
                policy=policy,
            )
        )
    return normalized


@app.get("/agent-routing", response_model=AgentRoutingConfigResponse)
async def get_agent_routing() -> AgentRoutingConfigResponse:
    return _build_routing_config_response()


@app.put("/agent-routing", response_model=AgentRoutingConfigResponse)
async def update_agent_routing(
    payload: AgentRoutingConfigUpdateRequest,
) -> AgentRoutingConfigResponse:
    agent_router.update_config(
        default_agent=payload.default_agent,
        rules=[
            {
                "id": rule.id,
                "agent": rule.agent,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "keywords": list(rule.keywords),
            }
            for rule in payload.rules
        ],
    )
    return _build_routing_config_response()


@app.post("/agent-routing/reload", response_model=AgentRoutingConfigResponse)
async def reload_agent_routing() -> AgentRoutingConfigResponse:
    agent_router.reload()
    return _build_routing_config_response()


@app.post(
    "/v3/workflows/runs",
    response_model=WorkflowRun,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_run(payload: CreateWorkflowRunRequest) -> WorkflowRun:
    return workflow_scheduler.create_run(
        project_id=payload.project_id,
        task_id=payload.task_id,
        template_id=payload.template_id,
        requested_by=payload.requested_by,
        summary=payload.summary,
    )


@app.get("/v3/workflows/runs/{run_id}", response_model=WorkflowRun)
async def get_workflow_run(run_id: str) -> WorkflowRun:
    try:
        return workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/v3/workflows/runs/{run_id}/workitems",
    response_model=WorkItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_workitem(run_id: str, payload: CreateWorkItemRequest) -> WorkItem:
    try:
        return workflow_scheduler.add_workitem(
            run_id=run_id,
            role=payload.role,
            module_key=payload.module_key,
            assignee_agent=payload.assignee_agent,
            depends_on=payload.depends_on,
            priority=payload.priority,
            requires_approval=payload.requires_approval,
            discussion_budget=payload.discussion_budget,
            discussion_timeout_seconds=payload.discussion_timeout_seconds,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v3/workflows/runs/{run_id}/workitems", response_model=list[WorkItem])
async def list_workitems(run_id: str) -> list[WorkItem]:
    try:
        return workflow_scheduler.list_workitems(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v3/workflows/runs/{run_id}/gates", response_model=list[GateCheck])
async def list_workflow_gate_checks(run_id: str) -> list[GateCheck]:
    try:
        return workflow_scheduler.list_gate_checks(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v3/workflows/runs/{run_id}/artifacts", response_model=list[Artifact])
async def list_workflow_artifacts(run_id: str) -> list[Artifact]:
    try:
        return workflow_scheduler.list_artifacts(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v3/workflows/runs/{run_id}/tick", response_model=list[WorkItem])
async def tick_workflow_run(run_id: str) -> list[WorkItem]:
    try:
        return workflow_scheduler.tick(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v3/workflows/workitems/{workitem_id}/start", response_model=WorkItem)
async def start_workitem(workitem_id: str) -> WorkItem:
    try:
        return workflow_scheduler.start_workitem(workitem_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v3/workflows/workitems/{workitem_id}/approve", response_model=WorkItem)
async def approve_workitem(
    workitem_id: str,
    payload: ApproveWorkItemRequest,
) -> WorkItem:
    try:
        return workflow_scheduler.approve_workitem(workitem_id, approved_by=payload.approved_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v3/workflows/workitems/{workitem_id}/complete", response_model=WorkItem)
async def complete_workitem(
    workitem_id: str,
    payload: CompleteWorkItemRequest,
) -> WorkItem:
    try:
        return workflow_scheduler.complete_workitem(workitem_id, success=payload.success)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(
    "/v3/workflows/runs/{run_id}/bootstrap",
    response_model=list[WorkItem],
)
async def bootstrap_workflow_run(
    run_id: str,
    payload: BootstrapWorkflowRequest,
) -> list[WorkItem]:
    try:
        result = workflow_engine.bootstrap_standard_pipeline(run_id, payload.modules)
        return result.workitems
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/v3/workflows/runs/{run_id}/execute",
    response_model=ExecuteWorkflowRunResponse,
)
async def execute_workflow_run(
    run_id: str,
    payload: ExecuteWorkflowRunRequest,
) -> ExecuteWorkflowRunResponse:
    try:
        return await workflow_engine.execute_until_blocked(
            run_id=run_id,
            max_loops=payload.max_loops,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get(
    "/v3/workflows/workitems/{workitem_id}/discussions",
    response_model=list[DiscussionSession],
)
async def list_workitem_discussions(workitem_id: str) -> list[DiscussionSession]:
    try:
        return workflow_scheduler.list_discussions(workitem_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/v3/workflows/workitems/{workitem_id}/discussion/resolve",
    response_model=DiscussionSession,
)
async def resolve_workitem_discussion(
    workitem_id: str,
    payload: ResolveDiscussionRequest,
) -> DiscussionSession:
    try:
        return workflow_scheduler.resolve_discussion(
            workitem_id,
            decision=payload.decision,
            resolved_by_role=payload.resolved_by,
            discussion_id=payload.discussion_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
