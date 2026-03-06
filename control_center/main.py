import os
import time
import json
import hashlib
import re
import shlex
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
    DecomposeBootstrapWorkflowRequest,
    DecomposeBootstrapWorkflowResponse,
    ConfirmDecomposeBootstrapWorkflowRequest,
    ConfirmDecomposeBootstrapWorkflowResponse,
    DecomposeBootstrapPendingWorkflowResponse,
    DecomposeBootstrapAggregateStatusResponse,
    DecomposeBootstrapAdvanceRequest,
    DecomposeBootstrapAdvanceResponse,
    DecomposeBootstrapAdvanceLoopRequest,
    DecomposeBootstrapAdvanceLoopResponse,
    WorkflowRunOrchestrateStrategy,
    WorkflowRunOrchestrateDecomposePayload,
    WorkflowRunOrchestrateDecompositionSummary,
    WorkflowRunOrchestrateRecoveryActionScore,
    WorkflowRunOrchestrateExecutionProfile,
    WorkflowRunOrchestrateDecisionMachineReport,
    WorkflowRunOrchestrateDecisionReport,
    WorkflowRunOrchestrateTelemetrySnapshot,
    WorkflowRunOrchestrateTelemetryRecord,
    WorkflowRunOrchestrateLatestTelemetryResponse,
    WorkflowRunOrchestrateRecoveryExecuteRequest,
    WorkflowRunOrchestrateRecoveryExecuteResponse,
    WorkflowRunOrchestrateRequest,
    WorkflowRunOrchestrateResponse,
    DecomposeBootstrapPreviewTask,
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
try:
    ACTION_LAYER_TIMEOUT_SECONDS = float(
        os.getenv("ACTION_LAYER_TIMEOUT_SECONDS", "30")
    )
except ValueError:
    ACTION_LAYER_TIMEOUT_SECONDS = 30.0
action_layer = ActionLayerClient(
    base_url=os.getenv("ACTION_LAYER_BASE_URL", "http://127.0.0.1:8100"),
    timeout_seconds=ACTION_LAYER_TIMEOUT_SECONDS,
)
agent_router = AgentRouter(
    os.getenv("WHERECODE_AGENT_ROUTING_FILE", "control_center/agents.routing.json")
)
AUTH_ENABLED = os.getenv("WHERECODE_AUTH_ENABLED", "true").lower() == "true"
AUTH_TOKEN = os.getenv("WHERECODE_TOKEN", "change-me")
DECOMPOSE_REQUIRE_EXPLICIT_MAP = (
    os.getenv("WHERECODE_DECOMPOSE_REQUIRE_EXPLICIT_MAP", "true").lower() == "true"
)
DECOMPOSE_REQUIRE_TASK_PACKAGE = (
    os.getenv("WHERECODE_DECOMPOSE_REQUIRE_TASK_PACKAGE", "true").lower() == "true"
)
DECOMPOSE_REQUIRE_CONFIRMATION = (
    os.getenv("WHERECODE_DECOMPOSE_REQUIRE_CONFIRMATION", "true").lower() == "true"
)
DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK = (
    os.getenv("WHERECODE_DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK", "true").lower() == "true"
)
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
COMMAND_ORCHESTRATE_POLICY_ENABLED = (
    os.getenv("WHERECODE_COMMAND_ORCHESTRATE_POLICY_ENABLED", "true").lower() == "true"
)
COMMAND_ORCHESTRATE_PREFIXES = tuple(
    item.strip()
    for item in os.getenv(
        "WHERECODE_COMMAND_ORCHESTRATE_PREFIXES",
        "/orchestrate,orchestrate:,编排:,主流程:",
    ).split(",")
    if item.strip()
)
try:
    COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES = int(
        os.getenv("WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES", "6")
    )
except ValueError:
    COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES = 6
if COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES < 1:
    COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES = 1
if COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES > 20:
    COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES = 20
COMMAND_ORCHESTRATE_DEFAULT_STRATEGY = os.getenv(
    "WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_STRATEGY",
    WorkflowRunOrchestrateStrategy.BALANCED.value,
).strip()


def _parse_bool_text(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _parse_int_text(value: str, *, minimum: int, maximum: int) -> int | None:
    try:
        parsed = int(value.strip())
    except ValueError:
        return None
    if parsed < minimum or parsed > maximum:
        return None
    return parsed


def _coerce_orchestrate_strategy(value: str | None) -> WorkflowRunOrchestrateStrategy:
    raw = (value or "").strip().lower()
    if not raw:
        raw = COMMAND_ORCHESTRATE_DEFAULT_STRATEGY.lower()
    try:
        return WorkflowRunOrchestrateStrategy(raw)
    except ValueError:
        return WorkflowRunOrchestrateStrategy.BALANCED


def _extract_command_orchestrate_intent(
    command: Command,
) -> dict[str, object] | None:
    if not COMMAND_ORCHESTRATE_POLICY_ENABLED:
        return None

    raw_text = command.text.strip()
    if not raw_text:
        return None

    matched_prefix = None
    lowered_text = raw_text.lower()
    for prefix in COMMAND_ORCHESTRATE_PREFIXES:
        normalized_prefix = prefix.strip()
        if not normalized_prefix:
            continue
        if lowered_text.startswith(normalized_prefix.lower()):
            matched_prefix = raw_text[: len(normalized_prefix)]
            break
    if matched_prefix is None:
        return None

    payload_text = raw_text[len(matched_prefix) :].strip()
    tokens: list[str]
    try:
        tokens = shlex.split(payload_text) if payload_text else []
    except ValueError:
        tokens = payload_text.split()

    flags: dict[str, str] = {}
    requirements_tokens: list[str] = []
    for token in tokens:
        normalized = token.strip()
        if normalized.startswith("--") and "=" in normalized:
            flag_key, flag_value = normalized[2:].split("=", 1)
            key = flag_key.strip().lower().replace("_", "-")
            value = flag_value.strip()
            if key and value:
                flags[key] = value
            continue
        requirements_tokens.append(normalized)

    requirements = " ".join(item for item in requirements_tokens if item).strip()
    module_hints_raw = (
        flags.get("module-hints")
        or flags.get("hints")
        or ""
    )
    module_hints: list[str] = []
    if module_hints_raw:
        for item in re.split(r"[,\|]", module_hints_raw):
            normalized = item.strip()
            if normalized and normalized not in module_hints:
                module_hints.append(normalized)

    max_modules = _parse_int_text(
        flags.get("max-modules", ""),
        minimum=1,
        maximum=20,
    )
    if max_modules is None:
        max_modules = COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES

    execute = _parse_bool_text(flags.get("execute", ""))
    if execute is None:
        execute = True
    force_redecompose = _parse_bool_text(flags.get("force-redecompose", ""))
    if force_redecompose is None:
        force_redecompose = False
    auto_advance_decompose = _parse_bool_text(flags.get("auto-advance-decompose", ""))
    if auto_advance_decompose is None:
        auto_advance_decompose = True
    auto_advance_force_refresh_preview = _parse_bool_text(
        flags.get("auto-advance-force-refresh-preview", "")
    )
    if auto_advance_force_refresh_preview is None:
        auto_advance_force_refresh_preview = False

    execute_max_loops = _parse_int_text(
        flags.get("execute-max-loops", ""),
        minimum=1,
        maximum=1000,
    )
    if execute_max_loops is None:
        execute_max_loops = 20

    auto_advance_max_steps = _parse_int_text(
        flags.get("auto-advance-max-steps", ""),
        minimum=1,
        maximum=100,
    )
    if auto_advance_max_steps is None:
        auto_advance_max_steps = 8

    auto_advance_execute_max_loops = _parse_int_text(
        flags.get("auto-advance-execute-max-loops", ""),
        minimum=1,
        maximum=1000,
    )

    expected_modules_raw = flags.get("expected-modules", "") or ""
    expected_modules: list[str] = []
    if expected_modules_raw:
        for item in re.split(r"[,\|]", expected_modules_raw):
            normalized = item.strip()
            if normalized and normalized not in expected_modules:
                expected_modules.append(normalized)

    return {
        "requirements": requirements,
        "module_hints": module_hints,
        "max_modules": max_modules,
        "strategy": _coerce_orchestrate_strategy(flags.get("strategy")),
        "execute": execute,
        "force_redecompose": force_redecompose,
        "auto_advance_decompose": auto_advance_decompose,
        "auto_advance_max_steps": auto_advance_max_steps,
        "auto_advance_execute_max_loops": auto_advance_execute_max_loops,
        "auto_advance_force_refresh_preview": auto_advance_force_refresh_preview,
        "execute_max_loops": execute_max_loops,
        "decompose_confirmed_by": flags.get("confirmed-by"),
        "decompose_confirmation_token": flags.get("confirmation-token"),
        "decompose_expected_modules": expected_modules,
        "requested_by": flags.get("requested-by") or command.requested_by,
        "source_prefix": matched_prefix.strip(),
    }


def _create_command_orchestrate_run(
    *,
    task: Task,
    command: Command,
    requirements: str,
) -> WorkflowRun:
    run = workflow_scheduler.create_run(
        project_id=task.project_id,
        task_id=task.id,
        requested_by=command.requested_by,
        summary=(requirements[:200] if requirements else None),
    )
    task.metadata["workflow_run_id_latest"] = run.id
    task.metadata["workflow_run_source"] = "command_orchestrate_policy"
    task.metadata["workflow_run_updated_at"] = now_utc().isoformat()
    return run


def _build_command_orchestrate_state_snapshot(
    *,
    run: WorkflowRun,
    orchestrate_result: WorkflowRunOrchestrateResponse,
    source_command_id: str,
) -> dict[str, object]:
    decision_machine = (
        orchestrate_result.decision_report.machine
        if orchestrate_result.decision_report is not None
        else None
    )
    return {
        "workflow_run_id": run.id,
        "source_command_id": source_command_id,
        "run_status": orchestrate_result.status_after.run_status,
        "orchestration_status": orchestrate_result.orchestration_status,
        "orchestration_reason": orchestrate_result.reason,
        "strategy": orchestrate_result.strategy.value,
        "actions": orchestrate_result.actions,
        "next_action": orchestrate_result.status_after.next_action,
        "workitem_total": orchestrate_result.status_after.workitem_total,
        "pending_confirmation": orchestrate_result.status_after.has_pending_confirmation,
        "primary_recovery_action": (
            decision_machine.primary_recovery_action
            if decision_machine is not None
            else None
        ),
        "primary_recovery_priority": (
            decision_machine.primary_recovery_priority
            if decision_machine is not None
            else None
        ),
        "primary_recovery_confidence": (
            decision_machine.primary_recovery_confidence
            if decision_machine is not None
            else None
        ),
        "recovery_actions": (
            decision_machine.recovery_actions
            if decision_machine is not None
            else []
        ),
        "updated_at": now_utc().isoformat(),
    }


async def execute_with_action_layer(command: Command, task: Task) -> ActionExecuteResponse:
    orchestrate_intent = _extract_command_orchestrate_intent(command)
    if orchestrate_intent is not None:
        requirements = str(orchestrate_intent.get("requirements", "")).strip()
        run = _create_command_orchestrate_run(
            task=task,
            command=command,
            requirements=requirements,
        )
        try:
            orchestrate_result = await orchestrate_workflow_run(
                run_id=run.id,
                payload=WorkflowRunOrchestrateRequest(
                    strategy=orchestrate_intent["strategy"],
                    requirements=(requirements or None),
                    module_hints=orchestrate_intent["module_hints"],
                    max_modules=orchestrate_intent["max_modules"],
                    requested_by=orchestrate_intent["requested_by"],
                    decompose_payload=None,
                    force_redecompose=orchestrate_intent["force_redecompose"],
                    execute=orchestrate_intent["execute"],
                    execute_max_loops=orchestrate_intent["execute_max_loops"],
                    auto_advance_decompose=orchestrate_intent["auto_advance_decompose"],
                    auto_advance_max_steps=orchestrate_intent["auto_advance_max_steps"],
                    auto_advance_execute_max_loops=orchestrate_intent[
                        "auto_advance_execute_max_loops"
                    ],
                    auto_advance_force_refresh_preview=orchestrate_intent[
                        "auto_advance_force_refresh_preview"
                    ],
                    decompose_confirmed_by=orchestrate_intent["decompose_confirmed_by"],
                    decompose_confirmation_token=orchestrate_intent[
                        "decompose_confirmation_token"
                    ],
                    decompose_expected_modules=orchestrate_intent[
                        "decompose_expected_modules"
                    ],
                ),
            )
        except HTTPException as exc:
            state_snapshot = {
                "workflow_run_id": run.id,
                "source_command_id": command.id,
                "run_status": run.status.value,
                "orchestration_status": "failed",
                "orchestration_reason": str(exc.detail),
                "actions": [],
                "next_action": None,
                "primary_recovery_action": None,
                "recovery_actions": [],
                "updated_at": now_utc().isoformat(),
            }
            command.metadata["command_execution_mode"] = "orchestrate_policy"
            command.metadata["workflow_run_id"] = run.id
            command.metadata["orchestrate_http_status"] = exc.status_code
            command.metadata["workflow_state_latest"] = state_snapshot
            task.metadata["workflow_state_latest"] = state_snapshot
            task.metadata["workflow_run_id_latest"] = run.id
            task.metadata["workflow_run_source"] = "command_orchestrate_policy"
            task.metadata["workflow_run_updated_at"] = state_snapshot["updated_at"]
            run.metadata["task_workflow_state_latest"] = state_snapshot
            workflow_scheduler.persist_run(run.id)
            detail = str(exc.detail)
            return ActionExecuteResponse(
                status="failed",
                summary=f"orchestrate request failed: {detail}",
                agent="chief-architect",
                trace_id=f"act_orch_fail_{uuid4().hex[:8]}",
                metadata={
                    "workflow_run_id": run.id,
                    "orchestrate_http_status": exc.status_code,
                    "reason": detail,
                    "workflow_state_latest": state_snapshot,
                },
            )

        state_snapshot = _build_command_orchestrate_state_snapshot(
            run=run,
            orchestrate_result=orchestrate_result,
            source_command_id=command.id,
        )
        command.metadata["command_execution_mode"] = "orchestrate_policy"
        command.metadata["workflow_run_id"] = run.id
        command.metadata["orchestration_status"] = orchestrate_result.orchestration_status
        command.metadata["orchestration_reason"] = orchestrate_result.reason
        command.metadata["orchestration_actions"] = orchestrate_result.actions
        command.metadata["orchestration_strategy"] = orchestrate_result.strategy.value
        command.metadata["orchestration_next_action"] = orchestrate_result.status_after.next_action
        command.metadata["workflow_state_latest"] = state_snapshot
        decision_machine = (
            orchestrate_result.decision_report.machine
            if orchestrate_result.decision_report is not None
            else None
        )
        if decision_machine is not None:
            command.metadata["orchestration_primary_recovery_action"] = (
                decision_machine.primary_recovery_action
            )

        task.metadata["workflow_run_id_latest"] = run.id
        task.metadata["workflow_run_status_latest"] = orchestrate_result.status_after.run_status
        task.metadata["workflow_run_next_action_latest"] = (
            orchestrate_result.status_after.next_action
        )
        task.metadata["workflow_run_updated_at"] = now_utc().isoformat()
        task.metadata["workflow_state_latest"] = state_snapshot
        run.metadata["task_workflow_state_latest"] = state_snapshot
        workflow_scheduler.persist_run(run.id)

        summary = (
            f"orchestrate status={orchestrate_result.orchestration_status}; "
            f"run_id={run.id}; "
            f"actions={','.join(orchestrate_result.actions) if orchestrate_result.actions else 'none'}; "
            f"next_action={orchestrate_result.status_after.next_action or 'none'}"
        )
        result_status = (
            "failed"
            if orchestrate_result.orchestration_status == "blocked"
            else "success"
        )
        return ActionExecuteResponse(
            status=result_status,
            summary=summary if result_status == "success" else f"{summary}; reason={orchestrate_result.reason or 'blocked'}",
            agent="chief-architect",
            trace_id=f"act_orch_{uuid4().hex[:8]}",
            metadata={
                "mode": "orchestrate_policy",
                "workflow_run_id": run.id,
                "orchestration_status": orchestrate_result.orchestration_status,
                "orchestration_reason": orchestrate_result.reason,
                "orchestration_actions": orchestrate_result.actions,
                "strategy": orchestrate_result.strategy.value,
                "next_action": orchestrate_result.status_after.next_action,
                "source_prefix": orchestrate_intent["source_prefix"],
                "workflow_state_latest": state_snapshot,
            },
        )

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


def _build_chief_decompose_prompt(
    *,
    requirements: str,
    max_modules: int,
    module_hints: list[str],
    project_id: str,
    task_id: str | None,
) -> str:
    hints = ", ".join(item.strip() for item in module_hints if item.strip()) or "(none)"
    task_ref = task_id or "(none)"
    required_tags = _derive_required_coverage_tags(
        requirements=requirements,
        module_hints=module_hints,
    )
    required_tags_text = ", ".join(required_tags) if required_tags else "(none)"
    return "\n".join(
        [
            "Role: chief-architect",
            "Context: software development project module decomposition for implementation planning.",
            "Task: decompose requirements into executable development modules for workflow bootstrap.",
            "Output requirements:",
            "- Return strict JSON for action-layer schema.",
            "- status must be success.",
            "- metadata.modules must be array of module keys.",
            "- metadata.decomposition.requirement_points must list key requirement bullets.",
            "- metadata.decomposition.modules should include module_key/responsibility/coverage_tags.",
            "- metadata.decomposition.coverage_check should include covered_tags/missing_tags.",
            "- metadata.decomposition.requirement_module_map must map required_coverage_tags to module keys.",
            "- requirement_module_map must cover every required_coverage_tag.",
            "- metadata.decomposition.module_task_packages must map module_key to task items.",
            "- each task item must include role and objective.",
            "- task item may include depends_on_roles for module-internal DAG scheduling.",
            "- task item may include deliverable and priority (1..5).",
            "- each module task package must cover roles: module-dev/doc-manager/qa-test/security-review.",
            f"- module count must be 1..{max_modules}.",
            "- module key format: lower-kebab-case; short and concrete.",
            "- modules must be directly mappable to implementation ownership.",
            "- summary should be one short sentence describing decomposition quality.",
            "- if required coverage cannot be satisfied, return status=failed with reason.",
            f"project_id={project_id}",
            f"task_id={task_ref}",
            f"module_hints={hints}",
            f"required_coverage_tags={required_tags_text}",
            "requirements:",
            requirements.strip(),
        ]
    )


def _extract_modules_from_chief_response(
    response: ActionExecuteResponse,
    *,
    max_modules: int,
) -> list[str]:
    metadata_modules = _extract_modules_from_metadata(response.metadata)
    if metadata_modules:
        return metadata_modules[:max_modules]

    summary_modules = _extract_modules_from_summary(response.summary)
    if summary_modules:
        return summary_modules[:max_modules]
    return []


def _extract_modules_from_metadata(metadata: dict[str, object]) -> list[str]:
    if not isinstance(metadata, dict):
        return []

    candidates: list[object] = []
    direct_modules = metadata.get("modules")
    if isinstance(direct_modules, list):
        candidates.extend(direct_modules)

    module_keys = metadata.get("module_keys")
    if isinstance(module_keys, list):
        candidates.extend(module_keys)

    decomposition = metadata.get("decomposition")
    if isinstance(decomposition, dict):
        nested = decomposition.get("modules")
        if isinstance(nested, list):
            candidates.extend(nested)

    modules_json = metadata.get("modules_json")
    if isinstance(modules_json, str) and modules_json.strip():
        try:
            parsed = json.loads(modules_json)
            if isinstance(parsed, list):
                candidates.extend(parsed)
        except json.JSONDecodeError:
            pass

    return _normalize_module_candidates(candidates)


def _extract_modules_from_summary(summary: str) -> list[str]:
    raw = summary.strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        modules = parsed.get("modules")
        if isinstance(modules, list):
            return _normalize_module_candidates(modules)
    if isinstance(parsed, list):
        return _normalize_module_candidates(parsed)

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    by_prefix: list[object] = []
    for line in lines:
        if ":" not in line:
            continue
        prefix, value = line.split(":", 1)
        if prefix.strip().lower() in {"module", "module_key"} and value.strip():
            by_prefix.append(value.strip())
    if by_prefix:
        return _normalize_module_candidates(by_prefix)
    return []


def _normalize_module_candidates(values: list[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            candidate = value.strip()
        elif isinstance(value, dict):
            candidate = ""
            for key in ("module_key", "module", "key", "name"):
                raw = value.get(key)
                if isinstance(raw, str) and raw.strip():
                    candidate = raw.strip()
                    break
        else:
            candidate = ""

        if not candidate:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        output.append(candidate)
    return output


def _derive_required_coverage_tags(
    *,
    requirements: str,
    module_hints: list[str],
) -> list[str]:
    tags_by_keyword = _coverage_tag_keyword_map()
    haystack = f"{requirements} {' '.join(module_hints)}".lower()
    output: list[str] = []
    for tag, keywords in tags_by_keyword.items():
        if any(_keyword_matches_haystack(haystack, keyword) for keyword in keywords):
            output.append(tag)
    return output


def _extract_declared_coverage_tags(metadata: dict[str, object]) -> set[str]:
    if not isinstance(metadata, dict):
        return set()

    collected: set[str] = set()

    def _add(values: object) -> None:
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    collected.add(item.strip().lower())

    _add(metadata.get("coverage_tags"))

    decomposition = metadata.get("decomposition")
    if isinstance(decomposition, dict):
        _add(decomposition.get("coverage_tags"))
        module_items = decomposition.get("modules")
        if isinstance(module_items, list):
            for item in module_items:
                if isinstance(item, dict):
                    _add(item.get("coverage_tags"))
    return collected


def _infer_coverage_tags_from_module_keys(module_keys: list[str]) -> set[str]:
    detected: set[str] = set()
    for key in module_keys:
        detected.update(_infer_coverage_tags_from_module_key(key))
    return detected


def _infer_coverage_tags_from_module_key(module_key: str) -> set[str]:
    normalized = module_key.strip().lower()
    detected: set[str] = set()
    for tag, keywords in _coverage_tag_keyword_map().items():
        if any(_keyword_matches_haystack(normalized, keyword) for keyword in keywords):
            detected.add(tag)
    return detected


def _coverage_tag_keyword_map() -> dict[str, tuple[str, ...]]:
    return {
        "crawl": ("crawl", "crawler", "collect", "ingest", "抓取", "采集"),
        "sentiment": ("sentiment", "opinion", "舆情", "情绪"),
        "ai_interpret": ("ai", "llm", "interpret", "解读"),
        "value_eval": ("value", "valuation", "eval", "估值", "评估"),
        "industry": ("industry", "sector", "行业"),
        "theme": ("theme", "topic", "题材"),
        "report": ("report", "daily", "dashboard", "报告", "日报"),
    }


def _coverage_tag_default_module_map() -> dict[str, str]:
    return {
        "crawl": "crawl-ingestion",
        "sentiment": "sentiment-analysis",
        "ai_interpret": "ai-interpretation",
        "value_eval": "value-evaluation",
        "industry": "industry-analysis",
        "theme": "theme-analysis",
        "report": "reporting-dashboard",
    }


def _normalize_module_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        return ""
    if normalized[0].isdigit():
        normalized = f"module-{normalized}"
    return normalized


def _build_synthetic_decomposition_fallback(
    *,
    requirements: str,
    module_hints: list[str],
    max_modules: int,
) -> dict[str, object] | None:
    required_tags = _derive_required_coverage_tags(
        requirements=requirements,
        module_hints=module_hints,
    )
    modules: list[str] = []
    seen: set[str] = set()

    def _add_module(candidate: str) -> None:
        key = _normalize_module_key(candidate)
        if not key or key in seen:
            return
        seen.add(key)
        modules.append(key)

    for hint in module_hints:
        _add_module(hint)

    default_tag_modules = _coverage_tag_default_module_map()
    for tag in required_tags:
        if any(
            tag in _infer_coverage_tags_from_module_key(module_key)
            for module_key in modules
        ):
            continue
        fallback_module = default_tag_modules.get(tag, f"{tag}-module")
        _add_module(fallback_module)

    if not modules:
        _add_module("core-implementation")

    if len(modules) > max_modules:
        prioritized: list[str] = []
        remaining_tags = set(required_tags)
        for module in modules:
            module_tags = _infer_coverage_tags_from_module_key(module)
            if not prioritized or (remaining_tags and (module_tags & remaining_tags)):
                prioritized.append(module)
                remaining_tags -= module_tags
            if len(prioritized) >= max_modules:
                break
        if len(prioritized) < max_modules:
            for module in modules:
                if module in prioritized:
                    continue
                prioritized.append(module)
                if len(prioritized) >= max_modules:
                    break
        modules = prioritized[:max_modules]

    requirement_module_map = _infer_requirement_module_map_from_modules(modules)
    missing_tags = [tag for tag in required_tags if not requirement_module_map.get(tag)]
    if missing_tags:
        return None

    return {
        "modules": modules,
        "required_tags": required_tags,
        "requirement_module_map": requirement_module_map,
        "module_task_packages": _infer_default_task_packages(modules),
    }


def _keyword_matches_haystack(haystack: str, keyword: str) -> bool:
    needle = keyword.strip().lower()
    if not needle:
        return False
    if re.fullmatch(r"[a-z0-9_]+", needle):
        return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None
    return needle in haystack


def _validate_decomposition_coverage(
    *,
    requirements: str,
    module_hints: list[str],
    modules: list[str],
    chief_metadata: dict[str, object],
) -> tuple[list[str], list[str]]:
    required_tags = _derive_required_coverage_tags(
        requirements=requirements,
        module_hints=module_hints,
    )
    if not required_tags:
        return [], []

    detected_tags = _infer_coverage_tags_from_module_keys(modules)
    detected_tags.update(_extract_declared_coverage_tags(chief_metadata))
    missing_tags = [tag for tag in required_tags if tag not in detected_tags]
    return required_tags, missing_tags


def _validate_requirement_module_mapping(
    *,
    required_tags: list[str],
    modules: list[str],
    chief_metadata: dict[str, object],
) -> tuple[dict[str, list[str]], list[str], dict[str, list[str]], bool]:
    mapping, explicit = _extract_requirement_module_map(chief_metadata)

    if not mapping:
        mapping = _infer_requirement_module_map_from_modules(modules)

    modules_set = {item.strip() for item in modules if item.strip()}
    normalized_mapping: dict[str, list[str]] = {}
    invalid_modules: dict[str, list[str]] = {}
    for tag, raw_modules in mapping.items():
        valid_items: list[str] = []
        invalid_items: list[str] = []
        for module_key in raw_modules:
            normalized = module_key.strip()
            if not normalized:
                continue
            if normalized in modules_set:
                if normalized not in valid_items:
                    valid_items.append(normalized)
            else:
                if normalized not in invalid_items:
                    invalid_items.append(normalized)
        if valid_items:
            normalized_mapping[tag] = valid_items
        if invalid_items:
            invalid_modules[tag] = invalid_items

    missing_tags = [tag for tag in required_tags if not normalized_mapping.get(tag)]
    return normalized_mapping, missing_tags, invalid_modules, explicit


def _extract_requirement_module_map(
    chief_metadata: dict[str, object],
) -> tuple[dict[str, list[str]], bool]:
    if not isinstance(chief_metadata, dict):
        return {}, False

    mapping: dict[str, list[str]] = {}
    explicit = False

    def _upsert(tag_key: object, module_values: object) -> None:
        tag = str(tag_key).strip().lower()
        if not tag:
            return
        values: list[str] = []
        if isinstance(module_values, list):
            for item in module_values:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip())
        elif isinstance(module_values, str) and module_values.strip():
            values.append(module_values.strip())
        if not values:
            return
        existing = mapping.get(tag, [])
        for module in values:
            if module not in existing:
                existing.append(module)
        mapping[tag] = existing

    direct_map = chief_metadata.get("requirement_module_map")
    if isinstance(direct_map, dict):
        explicit = True
        for key, value in direct_map.items():
            _upsert(key, value)

    decomposition = chief_metadata.get("decomposition")
    if isinstance(decomposition, dict):
        nested_map = decomposition.get("requirement_module_map")
        if isinstance(nested_map, dict):
            explicit = True
            for key, value in nested_map.items():
                _upsert(key, value)

        module_items = decomposition.get("modules")
        if isinstance(module_items, list):
            for item in module_items:
                if not isinstance(item, dict):
                    continue
                module_key = item.get("module_key")
                coverage_tags = item.get("coverage_tags")
                if isinstance(module_key, str) and module_key.strip() and isinstance(
                    coverage_tags, list
                ):
                    explicit = True
                    for tag in coverage_tags:
                        _upsert(tag, [module_key])

    return mapping, explicit


def _infer_requirement_module_map_from_modules(modules: list[str]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for module_key in modules:
        for tag in _infer_coverage_tags_from_module_key(module_key):
            existing = mapping.get(tag, [])
            if module_key not in existing:
                existing.append(module_key)
            mapping[tag] = existing
    return mapping


def _required_module_roles() -> tuple[str, ...]:
    return ("module-dev", "doc-manager", "qa-test", "security-review")


def _extract_module_task_packages(
    chief_metadata: dict[str, object],
) -> tuple[dict[str, list[dict[str, object]]], bool]:
    if not isinstance(chief_metadata, dict):
        return {}, False

    packages: dict[str, list[dict[str, object]]] = {}
    explicit = False

    def _normalize_task_items(value: object) -> list[dict[str, object]]:
        normalized_items: list[dict[str, object]] = []
        if not isinstance(value, list):
            return normalized_items
        for item in value:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip().lower()
            objective = str(
                item.get("objective")
                or item.get("goal")
                or item.get("task")
                or ""
            ).strip()
            if not role or not objective:
                continue
            deliverable = str(item.get("deliverable", "")).strip()
            row: dict[str, object] = {"role": role, "objective": objective}
            if deliverable:
                row["deliverable"] = deliverable
            raw_depends_on_roles = item.get("depends_on_roles")
            if raw_depends_on_roles is None:
                raw_depends_on_roles = item.get("depends_on")
            depends_on_roles: list[str] = []
            if isinstance(raw_depends_on_roles, str):
                normalized_dep = raw_depends_on_roles.strip().lower()
                if normalized_dep:
                    depends_on_roles.append(normalized_dep)
            elif isinstance(raw_depends_on_roles, list):
                for dep_item in raw_depends_on_roles:
                    normalized_dep = str(dep_item).strip().lower()
                    if not normalized_dep:
                        continue
                    if normalized_dep not in depends_on_roles:
                        depends_on_roles.append(normalized_dep)
            if depends_on_roles:
                row["depends_on_roles"] = depends_on_roles
            raw_priority = item.get("priority")
            if isinstance(raw_priority, int) and 1 <= raw_priority <= 5:
                row["priority"] = raw_priority
            normalized_items.append(row)
        return normalized_items

    def _upsert(module_key: object, tasks: object) -> None:
        module = str(module_key).strip()
        if not module:
            return
        normalized_tasks = _normalize_task_items(tasks)
        if not normalized_tasks:
            return
        existing = packages.get(module, [])
        for task in normalized_tasks:
            if task not in existing:
                existing.append(task)
        packages[module] = existing

    direct = chief_metadata.get("module_task_packages")
    if isinstance(direct, dict):
        explicit = True
        for module_key, tasks in direct.items():
            _upsert(module_key, tasks)

    decomposition = chief_metadata.get("decomposition")
    if isinstance(decomposition, dict):
        nested = decomposition.get("module_task_packages")
        if isinstance(nested, dict):
            explicit = True
            for module_key, tasks in nested.items():
                _upsert(module_key, tasks)

        module_items = decomposition.get("modules")
        if isinstance(module_items, list):
            for item in module_items:
                if not isinstance(item, dict):
                    continue
                module_key = item.get("module_key")
                task_package = item.get("task_package")
                if isinstance(module_key, str):
                    normalized_tasks = _normalize_task_items(task_package)
                    if normalized_tasks:
                        explicit = True
                        _upsert(module_key, normalized_tasks)

    return packages, explicit


def _infer_default_task_packages(modules: list[str]) -> dict[str, list[dict[str, str]]]:
    output: dict[str, list[dict[str, str]]] = {}
    for module in modules:
        tasks: list[dict[str, str]] = []
        for role in _required_module_roles():
            tasks.append(
                {
                    "role": role,
                    "objective": f"execute {role} stage for module {module}",
                }
            )
        output[module] = tasks
    return output


def _validate_module_task_packages(
    *,
    modules: list[str],
    chief_metadata: dict[str, object],
) -> tuple[
    dict[str, list[dict[str, object]]],
    list[str],
    dict[str, list[str]],
    dict[str, list[str]],
    bool,
]:
    packages, explicit = _extract_module_task_packages(chief_metadata)
    if not packages:
        packages = _infer_default_task_packages(modules)

    module_set = {item.strip() for item in modules if item.strip()}
    required_roles = set(_required_module_roles())

    normalized_packages: dict[str, list[dict[str, object]]] = {}
    missing_modules: list[str] = []
    invalid_roles: dict[str, list[str]] = {}
    missing_roles: dict[str, list[str]] = {}

    for module in modules:
        module_tasks = packages.get(module, [])
        if not module_tasks:
            missing_modules.append(module)
            continue

        role_seen: set[str] = set()
        normalized_tasks: list[dict[str, object]] = []
        current_invalid_roles: list[str] = []
        for task in module_tasks:
            role = str(task.get("role", "")).strip().lower()
            objective = str(task.get("objective", "")).strip()
            if not role or not objective:
                continue
            if role not in required_roles:
                if role not in current_invalid_roles:
                    current_invalid_roles.append(role)
                continue
            role_seen.add(role)
            row: dict[str, object] = {"role": role, "objective": objective}
            deliverable = str(task.get("deliverable", "")).strip()
            if deliverable:
                row["deliverable"] = deliverable
            raw_depends_on_roles = task.get("depends_on_roles")
            depends_on_roles: list[str] = []
            if isinstance(raw_depends_on_roles, list):
                for dep_item in raw_depends_on_roles:
                    normalized_dep = str(dep_item).strip().lower()
                    if not normalized_dep:
                        continue
                    if normalized_dep not in required_roles:
                        continue
                    if normalized_dep not in depends_on_roles:
                        depends_on_roles.append(normalized_dep)
            if depends_on_roles:
                row["depends_on_roles"] = depends_on_roles
            raw_priority = task.get("priority")
            if isinstance(raw_priority, int) and 1 <= raw_priority <= 5:
                row["priority"] = raw_priority
            if row not in normalized_tasks:
                normalized_tasks.append(row)

        if current_invalid_roles:
            invalid_roles[module] = current_invalid_roles

        missing_current_roles = sorted(required_roles - role_seen)
        if missing_current_roles:
            missing_roles[module] = missing_current_roles

        if normalized_tasks:
            normalized_packages[module] = normalized_tasks
        else:
            missing_modules.append(module)

    unknown_modules = sorted(set(packages.keys()) - module_set)
    for module in unknown_modules:
        invalid_roles[module] = invalid_roles.get(module, [])
        if "__unknown_module__" not in invalid_roles[module]:
            invalid_roles[module].append("__unknown_module__")

    return normalized_packages, missing_modules, invalid_roles, missing_roles, explicit


def _get_pending_decomposition(run: WorkflowRun) -> dict[str, object] | None:
    pending = run.metadata.get("pending_decomposition")
    if isinstance(pending, dict):
        return pending
    return None


def _get_pending_confirmation_status(pending: dict[str, object]) -> str:
    confirmation = pending.get("confirmation")
    if isinstance(confirmation, dict):
        value = str(confirmation.get("status", "")).strip().lower()
        if value:
            return value
    return "unknown"


def _optional_text(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _select_decomposition_for_preview(run: WorkflowRun) -> tuple[dict[str, object] | None, str]:
    pending = _get_pending_decomposition(run)
    if pending is not None:
        return pending, "pending"

    chief = run.metadata.get("chief_decomposition")
    if isinstance(chief, dict):
        return chief, "chief"

    return None, "none"


def _extract_preview_modules(decomposition: dict[str, object]) -> list[str]:
    raw_modules = decomposition.get("modules")
    if isinstance(raw_modules, list):
        modules = _normalize_module_candidates(raw_modules)
        if modules:
            return modules

    raw_chief_metadata = decomposition.get("chief_metadata")
    if isinstance(raw_chief_metadata, dict):
        return _extract_modules_from_metadata(raw_chief_metadata)
    return []


def _normalize_preview_depends_on_roles(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        role = str(item).strip().lower()
        if not role:
            continue
        if role not in output:
            output.append(role)
    return output


def _build_decompose_bootstrap_preview(
    *,
    run_id: str,
    source: str,
    generated_at: str,
    fingerprint: str,
    decomposition: dict[str, object],
) -> DecomposeBootstrapPreviewResponse:
    modules = _extract_preview_modules(decomposition)
    if not modules:
        raise ValueError("decomposition preview unavailable: no modules")

    (
        module_task_packages,
        missing_task_package_modules,
        invalid_task_package_roles,
        missing_task_package_roles,
        _task_package_explicit,
    ) = _validate_module_task_packages(
        modules=modules,
        chief_metadata=decomposition,
    )

    warnings: list[str] = []
    if missing_task_package_modules:
        warnings.append(
            "missing_task_package_modules=" + ",".join(sorted(missing_task_package_modules))
        )
    for module_key, roles in sorted(invalid_task_package_roles.items()):
        warnings.append(f"invalid_roles:{module_key}=>{','.join(sorted(roles))}")
    for module_key, roles in sorted(missing_task_package_roles.items()):
        warnings.append(f"missing_roles:{module_key}=>{','.join(sorted(roles))}")

    tasks: list[DecomposeBootstrapPreviewTask] = []
    levels: dict[str, int] = {}
    terminal_task_keys: list[str] = []

    for module in modules:
        package = module_task_packages.get(module, [])
        role_latest_task_key: dict[str, str] = {}
        module_task_keys: list[str] = []

        for index, item in enumerate(package, start=1):
            role = str(item.get("role", "")).strip().lower()
            objective = str(item.get("objective", "")).strip()
            if not role or not objective:
                continue

            task_key = f"{module}:{index}:{role}"
            depends_on_roles = _normalize_preview_depends_on_roles(item.get("depends_on_roles"))

            depends_on_task_keys: list[str] = []
            for depends_role in depends_on_roles:
                matched = role_latest_task_key.get(depends_role)
                if matched:
                    if matched not in depends_on_task_keys:
                        depends_on_task_keys.append(matched)
                else:
                    warnings.append(
                        f"depends_on_role_missing:{module}:{role}:{depends_role}:fallback=sequence"
                    )
            if not depends_on_task_keys and module_task_keys:
                depends_on_task_keys = [module_task_keys[-1]]

            level = 0
            for dependency_key in depends_on_task_keys:
                level = max(level, levels.get(dependency_key, 0) + 1)
            levels[task_key] = level

            priority_value = item.get("priority")
            priority = int(priority_value) if isinstance(priority_value, int) else 3
            if priority < 1 or priority > 5:
                priority = 3

            deliverable = _optional_text(item.get("deliverable"))
            task = DecomposeBootstrapPreviewTask(
                task_key=task_key,
                phase="module",
                module_key=module,
                role=role,
                objective=objective,
                priority=priority,
                deliverable=deliverable,
                depends_on_roles=depends_on_roles,
                depends_on_task_keys=depends_on_task_keys,
                level=level,
            )
            tasks.append(task)
            module_task_keys.append(task_key)
            role_latest_task_key[role] = task_key

        referenced_inside_module: set[str] = set()
        module_task_key_set = set(module_task_keys)
        for task in tasks:
            if task.task_key not in module_task_key_set:
                continue
            for dependency_key in task.depends_on_task_keys:
                if dependency_key in module_task_key_set:
                    referenced_inside_module.add(dependency_key)

        module_terminal_keys = [
            task_key
            for task_key in module_task_keys
            if task_key not in referenced_inside_module
        ]
        if not module_terminal_keys and module_task_keys:
            module_terminal_keys = [module_task_keys[-1]]
        terminal_task_keys.extend(module_terminal_keys)

    module_terminal_unique = list(dict.fromkeys(terminal_task_keys))
    global_stage_pairs = [
        ("integration-test", module_terminal_unique),
        ("acceptance", []),
        ("release-manager", []),
    ]
    latest_global_task_key = ""
    for role, preset_depends in global_stage_pairs:
        task_key = f"global:{role}"
        if role == "integration-test":
            depends_on_task_keys = preset_depends
        elif latest_global_task_key:
            depends_on_task_keys = [latest_global_task_key]
        else:
            depends_on_task_keys = []

        level = 0
        for dependency_key in depends_on_task_keys:
            level = max(level, levels.get(dependency_key, 0) + 1)
        levels[task_key] = level

        task = DecomposeBootstrapPreviewTask(
            task_key=task_key,
            phase="global",
            module_key="global",
            role=role,
            objective=f"execute {role} stage for global",
            priority=3,
            depends_on_roles=[],
            depends_on_task_keys=depends_on_task_keys,
            level=level,
        )
        tasks.append(task)
        latest_global_task_key = task_key

    grouped: dict[int, list[str]] = {}
    for task in tasks:
        grouped.setdefault(task.level, []).append(task.task_key)
    parallel_groups = [grouped[level] for level in sorted(grouped.keys())]

    return DecomposeBootstrapPreviewResponse(
        run_id=run_id,
        source=source,
        generated_at=generated_at,
        cache_hit=False,
        cache_fingerprint=fingerprint,
        modules=modules,
        task_count=len(tasks),
        terminal_task_keys=module_terminal_unique + ([latest_global_task_key] if latest_global_task_key else []),
        parallel_groups=parallel_groups,
        warnings=warnings,
        tasks=tasks,
    )


def _build_decompose_preview_fingerprint(decomposition: dict[str, object]) -> str:
    encoded = json.dumps(
        decomposition,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _get_cached_decompose_preview(
    run: WorkflowRun,
    *,
    fingerprint: str,
) -> DecomposeBootstrapPreviewResponse | None:
    cached = run.metadata.get("decompose_bootstrap_preview")
    if not isinstance(cached, dict):
        return None
    cached_fingerprint = str(cached.get("fingerprint", "")).strip()
    if not cached_fingerprint or cached_fingerprint != fingerprint:
        return None

    payload = cached.get("payload")
    if not isinstance(payload, dict):
        return None
    try:
        return DecomposeBootstrapPreviewResponse.model_validate(payload)
    except Exception:  # noqa: BLE001
        return None


def _get_preview_snapshot_status(
    run: WorkflowRun,
    *,
    decomposition: dict[str, object],
) -> tuple[bool, bool, str | None, str]:
    expected_fingerprint = _build_decompose_preview_fingerprint(decomposition)
    ready_snapshot = _get_cached_decompose_preview(
        run,
        fingerprint=expected_fingerprint,
    )
    if ready_snapshot is not None:
        return True, False, ready_snapshot.generated_at, expected_fingerprint

    cached = run.metadata.get("decompose_bootstrap_preview")
    if not isinstance(cached, dict):
        return False, False, None, expected_fingerprint

    cached_fingerprint = str(cached.get("fingerprint", "")).strip()
    payload = cached.get("payload")
    payload_generated_at = (
        _optional_text(payload.get("generated_at"))
        if isinstance(payload, dict)
        else None
    )
    if cached_fingerprint and cached_fingerprint != expected_fingerprint:
        return False, True, payload_generated_at, expected_fingerprint
    return False, False, payload_generated_at, expected_fingerprint


def _persist_decompose_preview(
    run: WorkflowRun,
    *,
    fingerprint: str,
    preview: DecomposeBootstrapPreviewResponse,
) -> None:
    run.metadata["decompose_bootstrap_preview"] = {
        "fingerprint": fingerprint,
        "payload": preview.model_dump(),
    }


def _extract_module_task_packages_from_decomposition(
    decomposition: dict[str, object],
) -> dict[str, list[dict[str, object]]] | None:
    raw_packages = decomposition.get("module_task_packages")
    if not isinstance(raw_packages, dict):
        return None

    normalized_packages: dict[str, list[dict[str, object]]] = {}
    for module_key, tasks in raw_packages.items():
        if not isinstance(module_key, str):
            continue
        if not isinstance(tasks, list):
            continue
        normalized_rows = [item for item in tasks if isinstance(item, dict)]
        if normalized_rows:
            normalized_packages[module_key] = normalized_rows
    return normalized_packages or None


def _build_workitem_status_counts(workitems: list[WorkItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in workitems:
        status_value = (
            item.status.value
            if hasattr(item.status, "value")
            else str(item.status).strip().lower()
        )
        counts[status_value] = counts.get(status_value, 0) + 1
    return {key: counts[key] for key in sorted(counts.keys())}


def _build_module_workitem_counts(workitems: list[WorkItem]) -> tuple[dict[str, int], int]:
    module_counts: dict[str, int] = {}
    global_count = 0
    for item in workitems:
        module_key = str(item.module_key or "").strip() or "global"
        if module_key == "global":
            global_count += 1
            continue
        module_counts[module_key] = module_counts.get(module_key, 0) + 1
    return ({key: module_counts[key] for key in sorted(module_counts.keys())}, global_count)


def _build_decompose_next_action(
    *,
    has_decomposition: bool,
    has_pending_confirmation: bool,
    preview_ready: bool,
    preview_stale: bool,
    workitem_total: int,
    workitem_status_counts: dict[str, int],
) -> str:
    if workitem_total > 0:
        ready_count = workitem_status_counts.get("ready", 0)
        if ready_count > 0:
            return "execute_workflow_run"

        unfinished_count = (
            workitem_status_counts.get("pending", 0)
            + workitem_status_counts.get("running", 0)
            + workitem_status_counts.get("waiting_approval", 0)
            + workitem_status_counts.get("needs_discussion", 0)
        )
        if unfinished_count > 0:
            return "wait_or_unblock_workitems"
        return "review_results"

    if not has_decomposition:
        return "trigger_decompose_bootstrap"
    if has_pending_confirmation:
        return "confirm_or_reject_decomposition"
    if preview_stale:
        return "refresh_preview"
    if not preview_ready:
        return "generate_preview"
    return "bootstrap_pipeline"


def _build_decompose_aggregate_status(
    *,
    run_id: str,
    run: WorkflowRun,
) -> DecomposeBootstrapAggregateStatusResponse:
    decomposition, source = _select_decomposition_for_preview(run)
    has_decomposition = decomposition is not None
    modules: list[str] = []
    preview_ready = False
    preview_stale = False
    preview_generated_at: str | None = None
    preview_fingerprint: str | None = None
    if decomposition is not None:
        modules = _extract_preview_modules(decomposition)
        (
            preview_ready,
            preview_stale,
            preview_generated_at,
            preview_fingerprint,
        ) = _get_preview_snapshot_status(
            run,
            decomposition=decomposition,
        )

    pending = _get_pending_decomposition(run)
    confirmation_status: str | None = None
    has_pending_confirmation = False
    if pending is not None:
        confirmation = pending.get("confirmation")
        if isinstance(confirmation, dict):
            confirmation_status = _optional_text(confirmation.get("status"))
            has_pending_confirmation = confirmation_status == "pending"
    elif isinstance(run.metadata.get("chief_decomposition"), dict):
        chief_confirmation = run.metadata["chief_decomposition"].get("confirmation")
        if isinstance(chief_confirmation, dict):
            confirmation_status = _optional_text(chief_confirmation.get("status"))

    workitems = workflow_scheduler.list_workitems(run_id)
    workitem_status_counts = _build_workitem_status_counts(workitems)
    module_workitem_counts, global_workitem_count = _build_module_workitem_counts(workitems)
    workitem_total = len(workitems)
    unfinished_count = (
        workitem_status_counts.get("pending", 0)
        + workitem_status_counts.get("ready", 0)
        + workitem_status_counts.get("running", 0)
        + workitem_status_counts.get("waiting_approval", 0)
        + workitem_status_counts.get("needs_discussion", 0)
    )
    bootstrap_started = workitem_total > 0
    bootstrap_finished = bootstrap_started and unfinished_count == 0
    next_action = _build_decompose_next_action(
        has_decomposition=has_decomposition,
        has_pending_confirmation=has_pending_confirmation,
        preview_ready=preview_ready,
        preview_stale=preview_stale,
        workitem_total=workitem_total,
        workitem_status_counts=workitem_status_counts,
    )
    return DecomposeBootstrapAggregateStatusResponse(
        run_id=run_id,
        run_status=run.status,
        decomposition_source=source,
        has_decomposition=has_decomposition,
        has_pending_confirmation=has_pending_confirmation,
        confirmation_status=confirmation_status,
        modules=modules,
        preview_ready=preview_ready,
        preview_stale=preview_stale,
        preview_generated_at=preview_generated_at,
        preview_fingerprint=preview_fingerprint,
        workitem_total=workitem_total,
        workitem_status_counts=workitem_status_counts,
        module_workitem_counts=module_workitem_counts,
        global_workitem_count=global_workitem_count,
        bootstrap_started=bootstrap_started,
        bootstrap_finished=bootstrap_finished,
        next_action=next_action,
    )


def _build_orchestrate_decomposition_summary(
    *,
    run: WorkflowRun,
    aggregate_status: DecomposeBootstrapAggregateStatusResponse,
) -> WorkflowRunOrchestrateDecompositionSummary | None:
    decomposition, source = _select_decomposition_for_preview(run)
    if decomposition is None:
        return None

    modules = _extract_preview_modules(decomposition)
    required_coverage_tags_raw = decomposition.get("required_coverage_tags")
    required_coverage_tags: list[str] = []
    if isinstance(required_coverage_tags_raw, list):
        for item in required_coverage_tags_raw:
            tag = _optional_text(item)
            if tag and tag not in required_coverage_tags:
                required_coverage_tags.append(tag)

    requirement_module_map = decomposition.get("requirement_module_map")
    mapped_requirement_tag_count = (
        len(requirement_module_map)
        if isinstance(requirement_module_map, dict)
        else 0
    )

    chief_metadata = decomposition.get("chief_metadata")
    requirement_points_count = 0
    if isinstance(chief_metadata, dict):
        nested_decomposition = chief_metadata.get("decomposition")
        if isinstance(nested_decomposition, dict):
            requirement_points = nested_decomposition.get("requirement_points")
            if isinstance(requirement_points, list):
                requirement_points_count = len(
                    [item for item in requirement_points if _optional_text(item)]
                )

    role_counts: dict[str, int] = {}
    module_task_count = 0
    module_task_packages = decomposition.get("module_task_packages")
    if isinstance(module_task_packages, dict):
        for tasks in module_task_packages.values():
            if not isinstance(tasks, list):
                continue
            for item in tasks:
                if not isinstance(item, dict):
                    continue
                module_task_count += 1
                role = _optional_text(item.get("role"))
                if role:
                    normalized_role = role.lower()
                    role_counts[normalized_role] = role_counts.get(normalized_role, 0) + 1

    confirmation_status = None
    pending = _get_pending_decomposition(run)
    if pending is not None:
        confirmation = pending.get("confirmation")
        if isinstance(confirmation, dict):
            confirmation_status = _optional_text(confirmation.get("status"))
    if confirmation_status is None:
        chief = run.metadata.get("chief_decomposition")
        if isinstance(chief, dict):
            confirmation = chief.get("confirmation")
            if isinstance(confirmation, dict):
                confirmation_status = _optional_text(confirmation.get("status"))

    return WorkflowRunOrchestrateDecompositionSummary(
        source=source,
        modules=modules,
        module_count=len(modules),
        module_task_count=module_task_count,
        module_task_role_counts={key: role_counts[key] for key in sorted(role_counts.keys())},
        required_coverage_tags=required_coverage_tags,
        mapped_requirement_tag_count=mapped_requirement_tag_count,
        requirement_points_count=requirement_points_count,
        confirmation_status=confirmation_status,
        has_pending_confirmation=aggregate_status.has_pending_confirmation,
        preview_ready=aggregate_status.preview_ready,
        preview_stale=aggregate_status.preview_stale,
        preview_generated_at=aggregate_status.preview_generated_at,
        workitem_total=aggregate_status.workitem_total,
        next_action=aggregate_status.next_action,
    )


def _build_orchestrate_decision_report(
    *,
    run_id: str,
    strategy: WorkflowRunOrchestrateStrategy,
    execution_profile: WorkflowRunOrchestrateExecutionProfile,
    orchestration_status: str,
    reason: str | None,
    actions: list[str],
    status_before: DecomposeBootstrapAggregateStatusResponse,
    status_after: DecomposeBootstrapAggregateStatusResponse,
) -> WorkflowRunOrchestrateDecisionReport:
    reason_lower = (reason or "").strip().lower()
    strategy_key = strategy.value
    scored_action_map: dict[str, WorkflowRunOrchestrateRecoveryActionScore] = {}

    strategy_score_adjustments: dict[str, dict[str, tuple[int, float]]] = {
        "speed": {
            "retry_with_decompose_payload": (-3, 0.03),
            "retry_bootstrap_pipeline": (-6, 0.08),
            "retry_execute_workflow_run": (-8, 0.1),
            "generate_preview": (-2, 0.02),
            "refresh_preview": (-1, 0.02),
            "reconfirm_decomposition": (6, -0.08),
            "wait_or_unblock_workitems": (8, -0.1),
        },
        "balanced": {
            "retry_with_decompose_payload": (-2, 0.02),
            "retry_bootstrap_pipeline": (-2, 0.04),
            "retry_execute_workflow_run": (-3, 0.05),
            "generate_preview": (-1, 0.01),
            "refresh_preview": (-2, 0.03),
            "reconfirm_decomposition": (1, -0.02),
            "wait_or_unblock_workitems": (2, -0.02),
        },
        "safe": {
            "reconfirm_with_latest_token": (-6, 0.06),
            "reconfirm_decomposition": (-5, 0.06),
            "refresh_preview": (-4, 0.05),
            "wait_or_unblock_workitems": (-2, 0.02),
            "retry_bootstrap_pipeline": (6, -0.06),
            "retry_execute_workflow_run": (10, -0.12),
        },
    }

    def _upsert_recovery_action_score(
        action: str,
        *,
        priority: int,
        confidence: float,
        reason_text: str,
    ) -> None:
        priority_delta, confidence_delta = strategy_score_adjustments.get(
            strategy_key,
            {},
        ).get(action, (0, 0.0))
        adjusted_priority = priority + priority_delta
        if adjusted_priority < 1:
            adjusted_priority = 1
        if adjusted_priority > 100:
            adjusted_priority = 100

        adjusted_confidence = confidence + confidence_delta
        if adjusted_confidence < 0:
            adjusted_confidence = 0.0
        if adjusted_confidence > 1:
            adjusted_confidence = 1.0

        existing = scored_action_map.get(action)
        if existing is None:
            scored_action_map[action] = WorkflowRunOrchestrateRecoveryActionScore(
                action=action,
                priority=adjusted_priority,
                confidence=adjusted_confidence,
                reason=reason_text,
            )
            return
        updated_priority = min(existing.priority, adjusted_priority)
        updated_confidence = max(existing.confidence, adjusted_confidence)
        updated_reason = existing.reason
        if updated_reason != reason_text and reason_text:
            updated_reason = f"{existing.reason}; {reason_text}"
        scored_action_map[action] = WorkflowRunOrchestrateRecoveryActionScore(
            action=action,
            priority=updated_priority,
            confidence=updated_confidence,
            reason=updated_reason,
        )

    if (
        "decompose_payload.requirements" in reason_lower
        or "requirements is required" in reason_lower
        or "decompose-bootstrap request payload is required" in reason_lower
    ):
        _upsert_recovery_action_score(
            "retry_with_decompose_payload",
            priority=10,
            confidence=0.95,
            reason_text="missing decomposition requirements payload",
        )
    if "force_redecompose is not allowed" in reason_lower:
        _upsert_recovery_action_score(
            "disable_force_redecompose",
            priority=15,
            confidence=0.95,
            reason_text="existing workitems forbid force redecompose",
        )
    if "confirmation token mismatch" in reason_lower:
        _upsert_recovery_action_score(
            "reconfirm_with_latest_token",
            priority=8,
            confidence=0.9,
            reason_text="confirmation token mismatch",
        )
    if status_after.has_pending_confirmation:
        _upsert_recovery_action_score(
            "reconfirm_decomposition",
            priority=12,
            confidence=0.9,
            reason_text="decomposition still pending confirmation",
        )
    if status_after.preview_stale:
        _upsert_recovery_action_score(
            "refresh_preview",
            priority=20,
            confidence=0.85,
            reason_text="preview snapshot stale",
        )

    next_action_hint_map: dict[str, tuple[str, int, float, str]] = {
        "generate_preview": ("generate_preview", 30, 0.8, "next action requires preview generation"),
        "refresh_preview": ("refresh_preview", 20, 0.85, "next action requires preview refresh"),
        "confirm_or_reject_decomposition": (
            "reconfirm_decomposition",
            12,
            0.9,
            "next action requires decomposition confirmation",
        ),
        "bootstrap_pipeline": ("retry_bootstrap_pipeline", 25, 0.75, "next action requires bootstrap"),
        "execute_workflow_run": (
            "retry_execute_workflow_run",
            35,
            0.7,
            "next action requires workflow execution",
        ),
        "wait_or_unblock_workitems": (
            "wait_or_unblock_workitems",
            45,
            0.6,
            "workitems are not ready yet",
        ),
        "trigger_decompose_bootstrap": (
            "retry_with_decompose_payload",
            10,
            0.95,
            "decompose bootstrap missing",
        ),
    }
    mapped_next_action = next_action_hint_map.get(status_after.next_action or "")
    if mapped_next_action:
        (
            next_action,
            next_priority,
            next_confidence,
            next_reason,
        ) = mapped_next_action
        _upsert_recovery_action_score(
            next_action,
            priority=next_priority,
            confidence=next_confidence,
            reason_text=next_reason,
        )

    if orchestration_status == "blocked" and not scored_action_map:
        _upsert_recovery_action_score(
            "retry_orchestrate",
            priority=60,
            confidence=0.5,
            reason_text="generic blocked fallback",
        )

    scored_recovery_actions = sorted(
        scored_action_map.values(),
        key=lambda item: (item.priority, -item.confidence, item.action),
    )
    recovery_actions = [item.action for item in scored_recovery_actions]
    primary_recovery_action = recovery_actions[0] if recovery_actions else None
    primary_recovery_priority = (
        scored_recovery_actions[0].priority
        if scored_recovery_actions
        else None
    )
    primary_recovery_confidence = (
        scored_recovery_actions[0].confidence
        if scored_recovery_actions
        else None
    )

    machine = WorkflowRunOrchestrateDecisionMachineReport(
        run_id=run_id,
        strategy=strategy,
        orchestration_status=orchestration_status,
        reason=reason,
        actions=actions,
        next_action_before=status_before.next_action,
        next_action_after=status_after.next_action,
        decompose_triggered=("decompose_bootstrap" in actions),
        execute_triggered=("execute_workflow_run" in actions),
        pending_confirmation_before=status_before.has_pending_confirmation,
        pending_confirmation_after=status_after.has_pending_confirmation,
        preview_ready_after=status_after.preview_ready,
        workitem_total_after=status_after.workitem_total,
        primary_recovery_action=primary_recovery_action,
        recovery_actions=recovery_actions,
        primary_recovery_priority=primary_recovery_priority,
        primary_recovery_confidence=primary_recovery_confidence,
        scored_recovery_actions=scored_recovery_actions,
        execution_profile=execution_profile,
    )
    action_text = ",".join(actions) if actions else "none"
    reason_text = reason if reason else "none"
    recovery_text = ",".join(recovery_actions) if recovery_actions else "none"
    primary_recovery_text = (
        f"{primary_recovery_action}:{primary_recovery_confidence:.2f}"
        if primary_recovery_action is not None and primary_recovery_confidence is not None
        else "none"
    )
    human_summary = (
        f"strategy={strategy.value}; "
        f"orchestrate_status={orchestration_status}; "
        f"actions={action_text}; "
        f"profile=execute:{execution_profile.execute_max_loops}/auto_steps:{execution_profile.auto_advance_max_steps}; "
        f"next_action={status_before.next_action or 'none'}->{status_after.next_action or 'none'}; "
        f"pending_confirmation={status_before.has_pending_confirmation}->{status_after.has_pending_confirmation}; "
        f"workitems_after={status_after.workitem_total}; "
        f"reason={reason_text}; "
        f"primary_recovery={primary_recovery_text}; "
        f"recovery_actions={recovery_text}"
    )
    return WorkflowRunOrchestrateDecisionReport(
        human_summary=human_summary,
        machine=machine,
    )


def _count_unfinished_workitems_from_aggregate_status(
    status: DecomposeBootstrapAggregateStatusResponse,
) -> int:
    counts = status.workitem_status_counts
    return (
        counts.get("pending", 0)
        + counts.get("ready", 0)
        + counts.get("running", 0)
        + counts.get("waiting_approval", 0)
        + counts.get("needs_discussion", 0)
    )


def _build_orchestrate_telemetry_snapshot(
    *,
    started_at: datetime,
    finished_at: datetime,
    actions: list[str],
    status_before: DecomposeBootstrapAggregateStatusResponse,
    status_after: DecomposeBootstrapAggregateStatusResponse,
    execute_result: ExecuteWorkflowRunResponse | None,
) -> WorkflowRunOrchestrateTelemetrySnapshot:
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    if duration_ms < 0:
        duration_ms = 0

    unfinished_before = _count_unfinished_workitems_from_aggregate_status(status_before)
    unfinished_after = _count_unfinished_workitems_from_aggregate_status(status_after)

    execute_run_status: str | None = None
    execute_failed_count: int | None = None
    execute_remaining_pending_count: int | None = None
    if execute_result is not None:
        execute_run_status = execute_result.run_status
        execute_failed_count = execute_result.failed_count
        execute_remaining_pending_count = execute_result.remaining_pending_count

    return WorkflowRunOrchestrateTelemetrySnapshot(
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        action_count=len(actions),
        actions=actions,
        workitem_total_before=status_before.workitem_total,
        workitem_total_after=status_after.workitem_total,
        workitem_total_delta=(status_after.workitem_total - status_before.workitem_total),
        unfinished_workitem_before=unfinished_before,
        unfinished_workitem_after=unfinished_after,
        unfinished_workitem_delta=(unfinished_after - unfinished_before),
        pending_confirmation_before=status_before.has_pending_confirmation,
        pending_confirmation_after=status_after.has_pending_confirmation,
        pending_confirmation_cleared=(
            status_before.has_pending_confirmation and not status_after.has_pending_confirmation
        ),
        preview_ready_before=status_before.preview_ready,
        preview_ready_after=status_after.preview_ready,
        preview_state_changed=(
            status_before.preview_ready != status_after.preview_ready
            or status_before.preview_stale != status_after.preview_stale
        ),
        next_action_before=status_before.next_action,
        next_action_after=status_after.next_action,
        next_action_changed=(status_before.next_action != status_after.next_action),
        decompose_triggered=("decompose_bootstrap" in actions),
        execute_triggered=("execute_workflow_run" in actions),
        execute_run_status=execute_run_status,
        execute_failed_count=execute_failed_count,
        execute_remaining_pending_count=execute_remaining_pending_count,
    )


def _read_orchestrate_latest_record(
    run: WorkflowRun,
) -> WorkflowRunOrchestrateTelemetryRecord | None:
    raw_value = run.metadata.get("orchestrate_telemetry_latest")
    if not isinstance(raw_value, dict):
        return None
    try:
        return WorkflowRunOrchestrateTelemetryRecord.model_validate(raw_value)
    except Exception:
        return None


def _persist_orchestrate_latest_record(
    *,
    run_id: str,
    run: WorkflowRun,
    strategy: WorkflowRunOrchestrateStrategy,
    orchestration_status: str,
    reason: str | None,
    actions: list[str],
    decision_report: WorkflowRunOrchestrateDecisionReport | None,
    telemetry_snapshot: WorkflowRunOrchestrateTelemetrySnapshot,
) -> WorkflowRunOrchestrateTelemetryRecord:
    record = WorkflowRunOrchestrateTelemetryRecord(
        run_id=run_id,
        strategy=strategy,
        orchestration_status=orchestration_status,
        reason=reason,
        actions=actions,
        decision_report=decision_report,
        telemetry_snapshot=telemetry_snapshot,
        recorded_at=now_utc(),
    )
    run.metadata["orchestrate_telemetry_latest"] = record.model_dump(mode="json")
    workflow_scheduler.persist_run(run_id)
    return record


def _resolve_orchestrate_recovery_action(
    *,
    payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
    latest_record: WorkflowRunOrchestrateTelemetryRecord | None,
) -> tuple[str | None, str]:
    explicit_action = _optional_text(payload.action)
    if explicit_action:
        return explicit_action.lower(), "request"
    if (
        latest_record is not None
        and latest_record.decision_report is not None
        and latest_record.decision_report.machine.primary_recovery_action
    ):
        return (
            latest_record.decision_report.machine.primary_recovery_action,
            "latest_primary",
        )
    return None, "none"


def _get_or_build_decompose_bootstrap_preview(
    *,
    run_id: str,
    run: WorkflowRun,
    refresh: bool,
) -> DecomposeBootstrapPreviewResponse:
    decomposition, source = _select_decomposition_for_preview(run)
    if decomposition is None:
        raise ValueError("no decomposition data to preview")

    fingerprint = _build_decompose_preview_fingerprint(decomposition)
    if not refresh:
        cached = _get_cached_decompose_preview(run, fingerprint=fingerprint)
        if cached is not None:
            return cached.model_copy(
                update={
                    "cache_hit": True,
                    "cache_fingerprint": fingerprint,
                }
            )

    preview = _build_decompose_bootstrap_preview(
        run_id=run_id,
        source=source,
        generated_at=now_utc().isoformat(),
        fingerprint=fingerprint,
        decomposition=decomposition,
    )
    _persist_decompose_preview(
        run,
        fingerprint=fingerprint,
        preview=preview,
    )
    workflow_scheduler.persist_run(run_id)
    return preview


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
    "/v3/workflows/runs/{run_id}/decompose-bootstrap",
    response_model=DecomposeBootstrapWorkflowResponse,
)
async def decompose_bootstrap_workflow_run(
    run_id: str,
    payload: DecomposeBootstrapWorkflowRequest,
) -> DecomposeBootstrapWorkflowResponse:
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pending = _get_pending_decomposition(run)
    if pending is not None and _get_pending_confirmation_status(pending) == "pending":
        raise HTTPException(
            status_code=409,
            detail="pending decomposition confirmation exists",
        )

    requested_by = payload.requested_by or run.requested_by or "control-center"
    action_request = ActionExecuteRequest(
        text=_build_chief_decompose_prompt(
            requirements=payload.requirements,
            max_modules=payload.max_modules,
            module_hints=payload.module_hints,
            project_id=run.project_id,
            task_id=run.task_id,
        ),
        role="chief-architect",
        project_id=run.project_id,
        task_id=run.task_id,
        requested_by=requested_by,
        module_key="workflow_decomposition",
    )

    try:
        chief_result = await action_layer.execute(action_request)
    except ActionLayerClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    chief_metadata: dict[str, object] = (
        dict(chief_result.metadata) if isinstance(chief_result.metadata, dict) else {}
    )
    fallback_applied = False
    fallback_reason: str | None = None

    if chief_result.status != "success":
        if not DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK:
            raise HTTPException(
                status_code=422,
                detail=f"chief decomposition failed: status={chief_result.status}",
            )
        synthetic = _build_synthetic_decomposition_fallback(
            requirements=payload.requirements,
            module_hints=payload.module_hints,
            max_modules=payload.max_modules,
        )
        if synthetic is None:
            raise HTTPException(
                status_code=422,
                detail=f"chief decomposition failed: status={chief_result.status}",
            )

        fallback_applied = True
        fallback_reason = f"chief status={chief_result.status}"
        modules = list(synthetic["modules"])
        required_tags = list(synthetic["required_tags"])
        missing_tags: list[str] = []
        requirement_module_map = dict(synthetic["requirement_module_map"])
        missing_mapping_tags: list[str] = []
        invalid_mapping_modules: dict[str, list[str]] = {}
        mapping_explicit = True
        module_task_packages = dict(synthetic["module_task_packages"])
        missing_task_package_modules: list[str] = []
        invalid_task_package_roles: dict[str, list[str]] = {}
        missing_task_package_roles: dict[str, list[str]] = {}
        task_package_explicit = True

        decomposition_meta = chief_metadata.get("decomposition")
        if not isinstance(decomposition_meta, dict):
            decomposition_meta = {}
        decomposition_meta["requirement_module_map"] = requirement_module_map
        decomposition_meta["module_task_packages"] = module_task_packages
        decomposition_meta["coverage_tags"] = required_tags
        decomposition_meta["synthetic_fallback"] = True
        decomposition_meta["synthetic_fallback_reason"] = fallback_reason
        chief_metadata["decomposition"] = decomposition_meta
        chief_metadata["requirement_module_map"] = requirement_module_map
        chief_metadata["module_task_packages"] = module_task_packages
        chief_metadata["coverage_tags"] = required_tags
        chief_metadata["modules"] = modules
        chief_metadata["synthetic_fallback"] = True
        chief_metadata["synthetic_fallback_reason"] = fallback_reason
    else:
        modules = _extract_modules_from_chief_response(
            chief_result,
            max_modules=payload.max_modules,
        )
        if not modules:
            raise HTTPException(
                status_code=422,
                detail="chief decomposition returned no modules",
            )

        required_tags, missing_tags = _validate_decomposition_coverage(
            requirements=payload.requirements,
            module_hints=payload.module_hints,
            modules=modules,
            chief_metadata=chief_metadata,
        )
        if missing_tags:
            raise HTTPException(
                status_code=422,
                detail=(
                    "chief decomposition missing required coverage tags: "
                    + ", ".join(missing_tags)
                ),
            )

        (
            requirement_module_map,
            missing_mapping_tags,
            invalid_mapping_modules,
            mapping_explicit,
        ) = _validate_requirement_module_mapping(
            required_tags=required_tags,
            modules=modules,
            chief_metadata=chief_metadata,
        )
        if required_tags and DECOMPOSE_REQUIRE_EXPLICIT_MAP and not mapping_explicit:
            raise HTTPException(
                status_code=422,
                detail="chief decomposition missing requirement-module mapping",
            )
        if invalid_mapping_modules:
            invalid_refs = ", ".join(
                f"{tag}=>{','.join(values)}"
                for tag, values in sorted(invalid_mapping_modules.items())
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "chief decomposition requirement-module mapping references unknown modules: "
                    + invalid_refs
                ),
            )
        if missing_mapping_tags:
            raise HTTPException(
                status_code=422,
                detail=(
                    "chief decomposition missing requirement-module mappings for tags: "
                    + ", ".join(missing_mapping_tags)
                ),
            )

        (
            module_task_packages,
            missing_task_package_modules,
            invalid_task_package_roles,
            missing_task_package_roles,
            task_package_explicit,
        ) = _validate_module_task_packages(
            modules=modules,
            chief_metadata=chief_metadata,
        )
        if modules and DECOMPOSE_REQUIRE_TASK_PACKAGE and not task_package_explicit:
            raise HTTPException(
                status_code=422,
                detail="chief decomposition missing module task packages",
            )
        if missing_task_package_modules:
            raise HTTPException(
                status_code=422,
                detail=(
                    "chief decomposition module task packages missing modules: "
                    + ", ".join(missing_task_package_modules)
                ),
            )
        if invalid_task_package_roles:
            invalid_role_text = ", ".join(
                f"{module}=>{','.join(roles)}"
                for module, roles in sorted(invalid_task_package_roles.items())
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "chief decomposition module task packages contain invalid roles: "
                    + invalid_role_text
                ),
            )
        if missing_task_package_roles:
            missing_role_text = ", ".join(
                f"{module}=>{','.join(roles)}"
                for module, roles in sorted(missing_task_package_roles.items())
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "chief decomposition module task packages missing required roles: "
                    + missing_role_text
                ),
            )

    chief_summary_text = chief_result.summary
    if fallback_applied:
        chief_summary_text = (
            f"{chief_result.summary}; synthetic decomposition fallback applied"
            if chief_result.summary
            else "synthetic decomposition fallback applied"
        )

    now_iso = now_utc().isoformat()
    decomposition_record = {
        "requirements": payload.requirements,
        "module_hints": payload.module_hints,
        "max_modules": payload.max_modules,
        "modules": modules,
        "required_coverage_tags": required_tags,
        "missing_coverage_tags": missing_tags,
        "requirement_module_map": requirement_module_map,
        "missing_mapping_tags": missing_mapping_tags,
        "invalid_mapping_modules": invalid_mapping_modules,
        "mapping_explicit": mapping_explicit,
        "module_task_packages": module_task_packages,
        "missing_task_package_modules": missing_task_package_modules,
        "invalid_task_package_roles": invalid_task_package_roles,
        "missing_task_package_roles": missing_task_package_roles,
        "task_package_explicit": task_package_explicit,
        "synthetic_fallback_applied": fallback_applied,
        "synthetic_fallback_reason": fallback_reason,
        "chief_status": chief_result.status,
        "chief_summary": chief_summary_text,
        "chief_agent": chief_result.agent,
        "chief_trace_id": chief_result.trace_id,
        "chief_metadata": chief_metadata,
    }
    if DECOMPOSE_REQUIRE_CONFIRMATION:
        confirmation_token = f"decomp_{uuid4().hex[:12]}"
        decomposition_record["confirmation"] = {
            "required": True,
            "status": "pending",
            "token": confirmation_token,
            "requested_by": requested_by,
            "requested_at": now_iso,
        }
        run.metadata["chief_decomposition"] = decomposition_record
        run.metadata["pending_decomposition"] = decomposition_record
        run.metadata.pop("decompose_bootstrap_preview", None)
        workflow_scheduler.persist_run(run_id)
        return DecomposeBootstrapWorkflowResponse(
            run_id=run_id,
            modules=modules,
            chief_summary=chief_summary_text,
            chief_agent=chief_result.agent,
            chief_trace_id=chief_result.trace_id,
            chief_metadata=chief_metadata,
            workitems=[],
            confirmation_required=True,
            confirmation_status="pending",
            confirmation_token=confirmation_token,
        )

    try:
        bootstrap = workflow_engine.bootstrap_standard_pipeline(
            run_id,
            modules,
            module_task_packages=module_task_packages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decomposition_record["confirmation"] = {
        "required": False,
        "status": "auto-approved",
        "confirmed_by": "system",
        "confirmed_at": now_iso,
    }
    run.metadata["chief_decomposition"] = decomposition_record
    run.metadata.pop("pending_decomposition", None)
    run.metadata.pop("decompose_bootstrap_preview", None)
    workflow_scheduler.persist_run(run_id)

    return DecomposeBootstrapWorkflowResponse(
        run_id=run_id,
        modules=modules,
        chief_summary=chief_summary_text,
        chief_agent=chief_result.agent,
        chief_trace_id=chief_result.trace_id,
        chief_metadata=chief_metadata,
        workitems=bootstrap.workitems,
        confirmation_required=False,
        confirmation_status="auto-approved",
        confirmation_token=None,
    )


@app.get(
    "/v3/workflows/runs/{run_id}/decompose-bootstrap/pending",
    response_model=DecomposeBootstrapPendingWorkflowResponse,
)
async def get_decompose_bootstrap_pending(
    run_id: str,
) -> DecomposeBootstrapPendingWorkflowResponse:
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pending = _get_pending_decomposition(run)
    if pending is None:
        return DecomposeBootstrapPendingWorkflowResponse(
            run_id=run_id,
            has_pending_confirmation=False,
        )

    confirmation = pending.get("confirmation")
    confirmation_payload = confirmation if isinstance(confirmation, dict) else {}
    confirmation_status = _optional_text(confirmation_payload.get("status"))

    pending_modules = pending.get("modules")
    modules = _normalize_module_candidates(pending_modules) if isinstance(pending_modules, list) else []

    raw_module_hints = pending.get("module_hints")
    module_hints: list[str] = []
    if isinstance(raw_module_hints, list):
        for hint in raw_module_hints:
            normalized_hint = _optional_text(hint)
            if normalized_hint:
                module_hints.append(normalized_hint)

    raw_chief_metadata = pending.get("chief_metadata")
    chief_metadata = raw_chief_metadata if isinstance(raw_chief_metadata, dict) else {}

    max_modules_value = pending.get("max_modules")
    max_modules = max_modules_value if isinstance(max_modules_value, int) else None
    (
        preview_ready,
        preview_stale,
        preview_generated_at,
        preview_fingerprint,
    ) = _get_preview_snapshot_status(
        run,
        decomposition=pending,
    )

    return DecomposeBootstrapPendingWorkflowResponse(
        run_id=run_id,
        has_pending_confirmation=confirmation_status == "pending",
        confirmation_status=confirmation_status,
        confirmation_token=_optional_text(confirmation_payload.get("token")),
        requested_by=_optional_text(confirmation_payload.get("requested_by")),
        requested_at=_optional_text(confirmation_payload.get("requested_at")),
        confirmed_by=_optional_text(confirmation_payload.get("confirmed_by")),
        confirmed_at=_optional_text(confirmation_payload.get("confirmed_at")),
        reason=_optional_text(confirmation_payload.get("reason")),
        requirements=_optional_text(pending.get("requirements")),
        module_hints=module_hints,
        max_modules=max_modules,
        modules=modules,
        chief_summary=_optional_text(pending.get("chief_summary")),
        chief_agent=_optional_text(pending.get("chief_agent")),
        chief_trace_id=_optional_text(pending.get("chief_trace_id")),
        chief_metadata=chief_metadata,
        preview_ready=preview_ready,
        preview_stale=preview_stale,
        preview_generated_at=preview_generated_at,
        preview_fingerprint=preview_fingerprint,
    )


@app.get(
    "/v3/workflows/runs/{run_id}/decompose-bootstrap/status",
    response_model=DecomposeBootstrapAggregateStatusResponse,
)
async def get_decompose_bootstrap_aggregate_status(
    run_id: str,
) -> DecomposeBootstrapAggregateStatusResponse:
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _build_decompose_aggregate_status(
        run_id=run_id,
        run=run,
    )


@app.get(
    "/v3/workflows/runs/{run_id}/decompose-bootstrap/preview",
    response_model=DecomposeBootstrapPreviewResponse,
)
async def get_decompose_bootstrap_preview(
    run_id: str,
    refresh: bool = False,
) -> DecomposeBootstrapPreviewResponse:
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return _get_or_build_decompose_bootstrap_preview(
            run_id=run_id,
            run=run,
            refresh=refresh,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if detail == "no decomposition data to preview" else 422
        raise HTTPException(status_code=status_code, detail=detail) from exc


async def _advance_decompose_bootstrap_once(
    run_id: str,
    *,
    confirmed_by: str | None,
    confirmation_token: str | None,
    expected_modules: list[str],
    execute_max_loops: int,
    force_refresh_preview: bool,
) -> DecomposeBootstrapAdvanceResponse:
    run = workflow_scheduler.get_run(run_id)
    status_before = _build_decompose_aggregate_status(
        run_id=run_id,
        run=run,
    )
    action_taken = status_before.next_action or "review_results"
    action_status = "noop"
    reason: str | None = None
    preview_result: DecomposeBootstrapPreviewResponse | None = None
    confirmation_result: ConfirmDecomposeBootstrapWorkflowResponse | None = None
    execute_result: ExecuteWorkflowRunResponse | None = None

    try:
        if action_taken in {"generate_preview", "refresh_preview"}:
            preview_result = _get_or_build_decompose_bootstrap_preview(
                run_id=run_id,
                run=run,
                refresh=(force_refresh_preview or action_taken == "refresh_preview"),
            )
            action_status = "executed"
        elif action_taken == "confirm_or_reject_decomposition":
            if not confirmed_by:
                action_status = "blocked"
                reason = "confirmed_by is required to auto-confirm pending decomposition"
            else:
                confirmation_result = await confirm_decompose_bootstrap_workflow_run(
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
            decomposition, _ = _select_decomposition_for_preview(run)
            if decomposition is None:
                action_status = "blocked"
                reason = "no decomposition record for bootstrap"
            else:
                modules = _extract_preview_modules(decomposition)
                if not modules:
                    action_status = "blocked"
                    reason = "decomposition has no valid modules"
                else:
                    workflow_engine.bootstrap_standard_pipeline(
                        run_id,
                        modules,
                        module_task_packages=_extract_module_task_packages_from_decomposition(
                            decomposition
                        ),
                    )
                    action_status = "executed"
        elif action_taken == "execute_workflow_run":
            execute_result = await workflow_engine.execute_until_blocked(
                run_id=run_id,
                max_loops=execute_max_loops,
            )
            action_status = "executed"
        elif action_taken == "wait_or_unblock_workitems":
            workflow_scheduler.tick(run_id)
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

    run_after = workflow_scheduler.get_run(run_id)
    status_after = _build_decompose_aggregate_status(
        run_id=run_id,
        run=run_after,
    )
    return DecomposeBootstrapAdvanceResponse(
        run_id=run_id,
        action_taken=action_taken,
        action_status=action_status,
        reason=reason,
        status_before=status_before,
        status_after=status_after,
        preview=preview_result,
        confirmation=confirmation_result,
        execute=execute_result,
    )


@app.post(
    "/v3/workflows/runs/{run_id}/decompose-bootstrap/advance",
    response_model=DecomposeBootstrapAdvanceResponse,
)
async def advance_decompose_bootstrap_run(
    run_id: str,
    payload: DecomposeBootstrapAdvanceRequest,
) -> DecomposeBootstrapAdvanceResponse:
    try:
        return await _advance_decompose_bootstrap_once(
            run_id,
            confirmed_by=payload.confirmed_by,
            confirmation_token=payload.confirmation_token,
            expected_modules=payload.expected_modules,
            execute_max_loops=payload.max_loops,
            force_refresh_preview=payload.force_refresh_preview,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/v3/workflows/runs/{run_id}/decompose-bootstrap/advance-loop",
    response_model=DecomposeBootstrapAdvanceLoopResponse,
)
async def advance_decompose_bootstrap_run_loop(
    run_id: str,
    payload: DecomposeBootstrapAdvanceLoopRequest,
) -> DecomposeBootstrapAdvanceLoopResponse:
    try:
        workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    steps: list[DecomposeBootstrapAdvanceResponse] = []
    halted_reason = "max_steps_reached"
    for _ in range(payload.max_steps):
        step = await _advance_decompose_bootstrap_once(
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

    if steps:
        final_status = steps[-1].status_after
    else:
        final_status = _build_decompose_aggregate_status(
            run_id=run_id,
            run=workflow_scheduler.get_run(run_id),
        )
        halted_reason = "no_steps"

    action_status_counts: dict[str, int] = {}
    action_taken_sequence: list[str] = []
    for step in steps:
        action_taken_sequence.append(step.action_taken)
        action_status_counts[step.action_status] = action_status_counts.get(step.action_status, 0) + 1

    return DecomposeBootstrapAdvanceLoopResponse(
        run_id=run_id,
        steps_executed=len(steps),
        halted_reason=halted_reason,
        last_action_taken=(steps[-1].action_taken if steps else None),
        action_taken_sequence=action_taken_sequence,
        action_status_counts=action_status_counts,
        final_status=final_status,
        steps=steps,
    )


@app.post(
    "/v3/workflows/runs/{run_id}/decompose-bootstrap/confirm",
    response_model=ConfirmDecomposeBootstrapWorkflowResponse,
)
async def confirm_decompose_bootstrap_workflow_run(
    run_id: str,
    payload: ConfirmDecomposeBootstrapWorkflowRequest,
) -> ConfirmDecomposeBootstrapWorkflowResponse:
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pending = _get_pending_decomposition(run)
    if pending is None:
        raise HTTPException(status_code=409, detail="no pending decomposition to confirm")

    confirmation = pending.get("confirmation")
    if not isinstance(confirmation, dict):
        raise HTTPException(status_code=409, detail="pending decomposition has no confirmation state")

    current_status = str(confirmation.get("status", "")).strip().lower()
    if current_status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"decomposition confirmation not pending: {current_status or 'unknown'}",
        )

    token = str(confirmation.get("token", "")).strip()
    if payload.confirmation_token and token and payload.confirmation_token != token:
        raise HTTPException(status_code=409, detail="confirmation token mismatch")

    pending_modules = pending.get("modules")
    if not isinstance(pending_modules, list):
        raise HTTPException(status_code=422, detail="pending decomposition has no modules")
    modules = _normalize_module_candidates(pending_modules)
    if not modules:
        raise HTTPException(status_code=422, detail="pending decomposition has no valid modules")

    if payload.expected_modules:
        expected_modules = _normalize_module_candidates(payload.expected_modules)
        if expected_modules != modules:
            raise HTTPException(status_code=409, detail="expected modules mismatch with pending decomposition")

    pending_task_packages = pending.get("module_task_packages")
    module_task_packages: dict[str, list[dict[str, object]]] | None = None
    if isinstance(pending_task_packages, dict):
        normalized_packages: dict[str, list[dict[str, object]]] = {}
        for module_key, tasks in pending_task_packages.items():
            if not isinstance(module_key, str):
                continue
            if not isinstance(tasks, list):
                continue
            normalized_rows = [item for item in tasks if isinstance(item, dict)]
            if normalized_rows:
                normalized_packages[module_key] = normalized_rows
        if normalized_packages:
            module_task_packages = normalized_packages

    confirmation["confirmed_by"] = payload.confirmed_by
    confirmation["confirmed_at"] = now_utc().isoformat()
    if payload.reason:
        confirmation["reason"] = payload.reason

    if not payload.approved:
        confirmation["status"] = "rejected"
        run.metadata["pending_decomposition"] = pending
        run.metadata["chief_decomposition"] = pending
        workflow_scheduler.persist_run(run_id)
        return ConfirmDecomposeBootstrapWorkflowResponse(
            run_id=run_id,
            approved=False,
            confirmation_status="rejected",
            confirmation_token=token or None,
            confirmed_by=payload.confirmed_by,
            reason=payload.reason,
            modules=modules,
            workitems=[],
        )

    try:
        bootstrap = workflow_engine.bootstrap_standard_pipeline(
            run_id,
            modules,
            module_task_packages=module_task_packages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    confirmation["status"] = "approved"
    run.metadata["chief_decomposition"] = pending
    run.metadata.pop("pending_decomposition", None)
    workflow_scheduler.persist_run(run_id)
    return ConfirmDecomposeBootstrapWorkflowResponse(
        run_id=run_id,
        approved=True,
        confirmation_status="approved",
        confirmation_token=token or None,
        confirmed_by=payload.confirmed_by,
        reason=payload.reason,
        modules=modules,
        workitems=bootstrap.workitems,
    )


@app.post(
    "/v3/workflows/runs/{run_id}/orchestrate",
    response_model=WorkflowRunOrchestrateResponse,
)
async def orchestrate_workflow_run(
    run_id: str,
    payload: WorkflowRunOrchestrateRequest,
) -> WorkflowRunOrchestrateResponse:
    started_at = now_utc()
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    status_before = _build_decompose_aggregate_status(
        run_id=run_id,
        run=run,
    )
    strategy = payload.strategy
    execute_max_loops = payload.execute_max_loops
    auto_advance_max_steps = payload.auto_advance_max_steps
    baseline_auto_advance_execute_max_loops = (
        payload.auto_advance_execute_max_loops
        if payload.auto_advance_execute_max_loops is not None
        else execute_max_loops
    )
    auto_advance_execute_max_loops = baseline_auto_advance_execute_max_loops
    auto_advance_force_refresh_preview = payload.auto_advance_force_refresh_preview
    if strategy == WorkflowRunOrchestrateStrategy.SAFE:
        execute_max_loops = min(execute_max_loops, 12)
        auto_advance_max_steps = min(auto_advance_max_steps, 5)
        auto_advance_execute_max_loops = min(baseline_auto_advance_execute_max_loops, 12)
        auto_advance_force_refresh_preview = True
    elif strategy == WorkflowRunOrchestrateStrategy.BALANCED:
        execute_max_loops = min(execute_max_loops, 16)
        auto_advance_max_steps = min(auto_advance_max_steps, 7)
        auto_advance_execute_max_loops = min(baseline_auto_advance_execute_max_loops, 16)
        auto_advance_force_refresh_preview = (
            auto_advance_force_refresh_preview or status_before.preview_stale
        )

    execution_profile = WorkflowRunOrchestrateExecutionProfile(
        auto_advance_decompose=payload.auto_advance_decompose,
        execute_max_loops=execute_max_loops,
        auto_advance_max_steps=auto_advance_max_steps,
        auto_advance_execute_max_loops=auto_advance_execute_max_loops,
        auto_advance_force_refresh_preview=auto_advance_force_refresh_preview,
    )

    decompose_payload = payload.decompose_payload
    if decompose_payload is None:
        inline_requirements = (payload.requirements or "").strip()
        if inline_requirements:
            decompose_payload = WorkflowRunOrchestrateDecomposePayload(
                requirements=inline_requirements,
                module_hints=payload.module_hints,
                max_modules=payload.max_modules,
                requested_by=payload.requested_by,
            )

    actions: list[str] = []
    orchestration_status = "noop"
    reason: str | None = None
    decompose_result: DecomposeBootstrapWorkflowResponse | None = None
    execute_result: ExecuteWorkflowRunResponse | None = None

    try:
        should_redecompose = payload.force_redecompose
        should_decompose_when_empty = (
            (not status_before.has_decomposition) and status_before.workitem_total == 0
        )
        should_decompose = should_redecompose or should_decompose_when_empty
        if should_redecompose and status_before.workitem_total > 0:
            orchestration_status = "blocked"
            reason = "force_redecompose is not allowed when workitems already exist"
        elif should_decompose:
            if decompose_payload is None:
                orchestration_status = "blocked"
                reason = (
                    "decompose_payload.requirements (or requirements) is required when decomposition is missing "
                    "or force_redecompose=true"
                )
            else:
                decompose_result = await decompose_bootstrap_workflow_run(
                    run_id,
                    DecomposeBootstrapWorkflowRequest(
                        requirements=decompose_payload.requirements,
                        max_modules=decompose_payload.max_modules,
                        module_hints=decompose_payload.module_hints,
                        requested_by=decompose_payload.requested_by,
                    ),
                )
                actions.append("decompose_bootstrap")

        if orchestration_status != "blocked" and payload.execute:
            actions.append("execute_workflow_run")
            execute_result = await execute_workflow_run(
                run_id,
                ExecuteWorkflowRunRequest(
                    max_loops=execute_max_loops,
                    auto_advance_decompose=payload.auto_advance_decompose,
                    auto_advance_max_steps=auto_advance_max_steps,
                    auto_advance_execute_max_loops=auto_advance_execute_max_loops,
                    auto_advance_force_refresh_preview=auto_advance_force_refresh_preview,
                    decompose_confirmed_by=payload.decompose_confirmed_by,
                    decompose_confirmation_token=payload.decompose_confirmation_token,
                    decompose_expected_modules=payload.decompose_expected_modules,
                ),
            )
    except HTTPException as exc:
        if exc.status_code in {409, 422}:
            orchestration_status = "blocked"
            reason = str(exc.detail)
        else:
            raise
    except ValueError as exc:
        orchestration_status = "blocked"
        reason = str(exc)

    if orchestration_status != "blocked":
        if execute_result is not None:
            orchestration_status = "executed"
        elif decompose_result is not None:
            orchestration_status = "prepared"
        else:
            orchestration_status = "noop"

    run_after = workflow_scheduler.get_run(run_id)
    status_after = _build_decompose_aggregate_status(
        run_id=run_id,
        run=run_after,
    )
    decomposition_summary = _build_orchestrate_decomposition_summary(
        run=run_after,
        aggregate_status=status_after,
    )
    decision_report = _build_orchestrate_decision_report(
        run_id=run_id,
        strategy=strategy,
        execution_profile=execution_profile,
        orchestration_status=orchestration_status,
        reason=reason,
        actions=actions,
        status_before=status_before,
        status_after=status_after,
    )
    telemetry_snapshot = _build_orchestrate_telemetry_snapshot(
        started_at=started_at,
        finished_at=now_utc(),
        actions=actions,
        status_before=status_before,
        status_after=status_after,
        execute_result=execute_result,
    )
    _persist_orchestrate_latest_record(
        run_id=run_id,
        run=run_after,
        strategy=strategy,
        orchestration_status=orchestration_status,
        reason=reason,
        actions=actions,
        decision_report=decision_report,
        telemetry_snapshot=telemetry_snapshot,
    )
    return WorkflowRunOrchestrateResponse(
        run_id=run_id,
        strategy=strategy,
        orchestration_status=orchestration_status,
        reason=reason,
        actions=actions,
        status_before=status_before,
        status_after=status_after,
        decomposition_summary=decomposition_summary,
        decision_report=decision_report,
        telemetry_snapshot=telemetry_snapshot,
        decompose=decompose_result,
        execute=execute_result,
    )

@app.get(
    "/v3/workflows/runs/{run_id}/orchestrate/latest",
    response_model=WorkflowRunOrchestrateLatestTelemetryResponse,
)
async def get_latest_orchestrate_telemetry(
    run_id: str,
) -> WorkflowRunOrchestrateLatestTelemetryResponse:
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    record = _read_orchestrate_latest_record(run)
    return WorkflowRunOrchestrateLatestTelemetryResponse(
        run_id=run_id,
        found=record is not None,
        record=record,
    )


@app.post(
    "/v3/workflows/runs/{run_id}/orchestrate/recover",
    response_model=WorkflowRunOrchestrateRecoveryExecuteResponse,
)
async def execute_orchestrate_recovery_action(
    run_id: str,
    payload: WorkflowRunOrchestrateRecoveryExecuteRequest,
) -> WorkflowRunOrchestrateRecoveryExecuteResponse:
    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    latest_record = _read_orchestrate_latest_record(run)
    selected_action, action_source = _resolve_orchestrate_recovery_action(
        payload=payload,
        latest_record=latest_record,
    )
    if not selected_action:
        return WorkflowRunOrchestrateRecoveryExecuteResponse(
            run_id=run_id,
            action_source=action_source,
            selected_action=None,
            action_status="blocked",
            reason="no recovery action in request or latest decision report",
            latest_record_before=latest_record,
        )

    orchestrate_result: WorkflowRunOrchestrateResponse | None = None
    preview_result: DecomposeBootstrapPreviewResponse | None = None
    confirmation_result: ConfirmDecomposeBootstrapWorkflowResponse | None = None
    advance_loop_result: DecomposeBootstrapAdvanceLoopResponse | None = None
    execute_result: ExecuteWorkflowRunResponse | None = None

    try:
        if selected_action in {"generate_preview", "refresh_preview"}:
            preview_result = await get_decompose_bootstrap_preview_run(
                run_id=run_id,
                refresh=(
                    selected_action == "refresh_preview"
                    or payload.auto_advance_force_refresh_preview
                ),
            )
        elif selected_action in {"reconfirm_decomposition", "reconfirm_with_latest_token"}:
            pending = _get_pending_decomposition(run)
            if pending is None:
                raise HTTPException(status_code=409, detail="no pending decomposition to confirm")
            if _get_pending_confirmation_status(pending) != "pending":
                raise HTTPException(status_code=409, detail="decomposition confirmation is not pending")
            confirmed_by = _optional_text(payload.confirmed_by)
            if not confirmed_by:
                raise HTTPException(
                    status_code=422,
                    detail="confirmed_by is required for decomposition confirmation",
                )
            confirmation_token = _optional_text(payload.confirmation_token)
            if selected_action == "reconfirm_with_latest_token" and not confirmation_token:
                confirmation = pending.get("confirmation")
                if isinstance(confirmation, dict):
                    confirmation_token = _optional_text(confirmation.get("token"))
            confirmation_result = await confirm_decompose_bootstrap_workflow_run(
                run_id=run_id,
                payload=ConfirmDecomposeBootstrapWorkflowRequest(
                    approved=True,
                    confirmed_by=confirmed_by,
                    reason=f"orchestrate recovery action: {selected_action}",
                    confirmation_token=confirmation_token,
                    expected_modules=payload.expected_modules,
                ),
            )
        elif selected_action == "retry_bootstrap_pipeline":
            advance_loop_result = await advance_decompose_bootstrap_run_loop(
                run_id=run_id,
                payload=DecomposeBootstrapAdvanceLoopRequest(
                    confirmed_by=payload.confirmed_by,
                    confirmation_token=payload.confirmation_token,
                    expected_modules=payload.expected_modules,
                    execute_max_loops=payload.execute_max_loops,
                    force_refresh_preview=payload.auto_advance_force_refresh_preview,
                    max_steps=payload.advance_loop_max_steps,
                    stop_when_bootstrap_finished=True,
                ),
            )
        elif selected_action in {"retry_execute_workflow_run", "wait_or_unblock_workitems"}:
            execute_result = await execute_workflow_run(
                run_id=run_id,
                payload=ExecuteWorkflowRunRequest(
                    max_loops=payload.execute_max_loops,
                    auto_advance_decompose=payload.auto_advance_decompose,
                    auto_advance_max_steps=payload.auto_advance_max_steps,
                    auto_advance_execute_max_loops=payload.auto_advance_execute_max_loops,
                    auto_advance_force_refresh_preview=payload.auto_advance_force_refresh_preview,
                    decompose_confirmed_by=payload.confirmed_by,
                    decompose_confirmation_token=payload.confirmation_token,
                    decompose_expected_modules=payload.expected_modules,
                ),
            )
        elif selected_action in {
            "retry_with_decompose_payload",
            "disable_force_redecompose",
            "retry_orchestrate",
        }:
            requirements = _optional_text(payload.requirements)
            if selected_action == "retry_with_decompose_payload" and not requirements:
                raise HTTPException(
                    status_code=422,
                    detail="requirements is required for retry_with_decompose_payload",
                )
            decompose_payload: WorkflowRunOrchestrateDecomposePayload | None = None
            if requirements:
                decompose_payload = WorkflowRunOrchestrateDecomposePayload(
                    requirements=requirements,
                    module_hints=payload.module_hints,
                    max_modules=payload.max_modules,
                    requested_by=payload.requested_by,
                )

            orchestrate_result = await orchestrate_workflow_run(
                run_id=run_id,
                payload=WorkflowRunOrchestrateRequest(
                    strategy=payload.strategy,
                    requirements=requirements,
                    module_hints=payload.module_hints,
                    max_modules=payload.max_modules,
                    requested_by=payload.requested_by,
                    decompose_payload=decompose_payload,
                    force_redecompose=False,
                    execute=payload.execute,
                    execute_max_loops=payload.execute_max_loops,
                    auto_advance_decompose=payload.auto_advance_decompose,
                    auto_advance_max_steps=payload.auto_advance_max_steps,
                    auto_advance_execute_max_loops=payload.auto_advance_execute_max_loops,
                    auto_advance_force_refresh_preview=payload.auto_advance_force_refresh_preview,
                    decompose_confirmed_by=payload.confirmed_by,
                    decompose_confirmation_token=payload.confirmation_token,
                    decompose_expected_modules=payload.expected_modules,
                ),
            )
        else:
            raise HTTPException(status_code=422, detail=f"unsupported recovery action: {selected_action}")

        return WorkflowRunOrchestrateRecoveryExecuteResponse(
            run_id=run_id,
            action_source=action_source,
            selected_action=selected_action,
            action_status="executed",
            reason=None,
            latest_record_before=latest_record,
            orchestrate=orchestrate_result,
            preview=preview_result,
            confirmation=confirmation_result,
            advance_loop=advance_loop_result,
            execute=execute_result,
        )
    except HTTPException as exc:
        if exc.status_code in {409, 422}:
            return WorkflowRunOrchestrateRecoveryExecuteResponse(
                run_id=run_id,
                action_source=action_source,
                selected_action=selected_action,
                action_status="blocked",
                reason=str(exc.detail),
                latest_record_before=latest_record,
                orchestrate=orchestrate_result,
                preview=preview_result,
                confirmation=confirmation_result,
                advance_loop=advance_loop_result,
                execute=execute_result,
            )
        raise
    except ValueError as exc:
        return WorkflowRunOrchestrateRecoveryExecuteResponse(
            run_id=run_id,
            action_source=action_source,
            selected_action=selected_action,
            action_status="blocked",
            reason=str(exc),
            latest_record_before=latest_record,
            orchestrate=orchestrate_result,
            preview=preview_result,
            confirmation=confirmation_result,
            advance_loop=advance_loop_result,
            execute=execute_result,
        )


@app.post(
    "/v3/workflows/runs/{run_id}/execute",
    response_model=ExecuteWorkflowRunResponse,
)
async def execute_workflow_run(
    run_id: str,
    payload: ExecuteWorkflowRunRequest,
) -> ExecuteWorkflowRunResponse:
    auto_advance_result: DecomposeBootstrapAdvanceLoopResponse | None = None
    if payload.auto_advance_decompose:
        try:
            auto_advance_result = await advance_decompose_bootstrap_run_loop(
                run_id,
                DecomposeBootstrapAdvanceLoopRequest(
                    confirmed_by=payload.decompose_confirmed_by,
                    confirmation_token=payload.decompose_confirmation_token,
                    expected_modules=payload.decompose_expected_modules,
                    execute_max_loops=(
                        payload.auto_advance_execute_max_loops
                        if payload.auto_advance_execute_max_loops is not None
                        else payload.max_loops
                    ),
                    force_refresh_preview=payload.auto_advance_force_refresh_preview,
                    max_steps=payload.auto_advance_max_steps,
                    stop_when_bootstrap_finished=False,
                ),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        run = workflow_scheduler.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pending = _get_pending_decomposition(run)
    if pending is not None and _get_pending_confirmation_status(pending) == "pending":
        detail = "decomposition confirmation required before execute"
        if auto_advance_result is not None and auto_advance_result.steps:
            last_step = auto_advance_result.steps[-1]
            if last_step.reason:
                detail = f"{detail}: {last_step.reason}"
        raise HTTPException(
            status_code=409,
            detail=detail,
        )

    try:
        execution_result = await workflow_engine.execute_until_blocked(
            run_id=run_id,
            max_loops=payload.max_loops,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if auto_advance_result is None:
        return execution_result
    updated_fields: dict[str, object] = {
        "decompose_auto_advance": auto_advance_result,
    }
    if execution_result.executed_count == 0 and execution_result.failed_count == 0:
        auto_exec_results = [
            step.execute
            for step in auto_advance_result.steps
            if step.execute is not None
        ]
        if auto_exec_results:
            auto_executed_ids: list[str] = []
            auto_failed_ids: list[str] = []
            for result in auto_exec_results:
                for workitem_id in result.executed_workitem_ids:
                    if workitem_id not in auto_executed_ids:
                        auto_executed_ids.append(workitem_id)
                for workitem_id in result.failed_workitem_ids:
                    if workitem_id not in auto_failed_ids:
                        auto_failed_ids.append(workitem_id)
            if auto_executed_ids:
                updated_fields["executed_workitem_ids"] = auto_executed_ids
                updated_fields["executed_count"] = len(auto_executed_ids)
            else:
                updated_fields["executed_count"] = max(
                    result.executed_count for result in auto_exec_results
                )
            if auto_failed_ids:
                updated_fields["failed_workitem_ids"] = auto_failed_ids
                updated_fields["failed_count"] = len(auto_failed_ids)
            else:
                updated_fields["failed_count"] = max(
                    result.failed_count for result in auto_exec_results
                )

    return execution_result.model_copy(update=updated_fields)


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
