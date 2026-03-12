# WhereCode Architecture V2

Updated: 2026-03-11

## Goal

Build a programmer-focused autonomous engineering orchestrator.

V2 baseline aligns to command-line autonomous coding tools (OpenClaw / OpenCode / Oh My OpenCode style):
- single command entry
- explicit plan/build modes
- explicit workflow modes (`test` full-flow, `dev` one-stage-per-run)
- autonomous execute loop
- structured run artifacts
- human checkpoint only at milestone boundaries

## System Layers

1. Command Center
- User input and run visibility.
- No business logic.

2. Control Center (Main Brain)
- Requirement decomposition.
- Workflow scheduling and role routing.
- Gate and recovery decisions.
- State persistence.
- Service modularization:
  - `api/action_layer_routes.py` owns action-layer proxy routes.
  - `api/agent_rules_routes.py` owns agent role-rules registry routes.
  - `api/agent_routing_routes.py` owns agent-routing routes.
  - `api/context_memory_routes.py` owns context/memory namespace routes.
  - `api/hierarchy_routes.py` owns project/task/command/snapshot hierarchy routes.
  - `api/metrics_routes.py` owns metrics and metrics-policy routes.
  - `api/runtime_config_routes.py` owns runtime config query routes.
  - `api/ops_check_routes.py` owns ops check HTTP routes (`/ops/checks/*`).
  - `api/workflow_core_routes.py` owns workflow core HTTP routes.
  - `api/workflow_execution_routes.py` owns workflow execute/discussion routes.
  - `api/workflow_orchestration_routes.py` owns workflow decompose/orchestrate/recover routes.
  - `services/app_wiring.py` owns app middleware/router wiring and ops-check runtime bootstrap.
  - `services/config_bootstrap.py` owns env/config parsing and normalized bootstrap config defaults.
  - `services/context_memory_store.py` owns context isolation memory namespaces (`shared`/`project`/`run`) and layered resolve.
  - `services/agent_rules_registry.py` owns role-rules registry loading/validation/export (`main`/`subproject` scopes).
  - `services/ops_check_runtime.py` owns ops check run lifecycle and persistence.
  - `services/workflow_execution_runtime.py` owns execute/interrupt run lifecycle (auto-advance + execution merge + cancel control).
  - workflow core supports run restart for canceled/terminal runs to continue execution on a new run id.
  - `services/workflow_decompose_helpers.py` owns chief decompose prompt construction and helper delegation.
  - `services/workflow_decompose_helpers_coverage.py` owns decompose coverage tag inference/mapping/fallback helper logic.
  - `services/workflow_decompose_helpers_tasks.py` owns module task-package extraction/validation/defaulting helper logic.
  - `services/workflow_decompose_preview_support.py` owns decompose preview/cache helper logic.
  - `services/workflow_decompose_runtime.py` owns decompose bootstrap + pending/status/preview/advance/confirm lifecycle.
  - `services/workflow_decompose_runtime_helpers.py` owns decompose runtime helper logic (chief-output validation, pending extraction, task-package normalization).
  - `services/workflow_decompose_runtime_policy.py` owns decompose runtime policy helpers (chief request/record/confirmation metadata + advance-loop summary).
  - `services/workflow_decompose_runtime_advance.py` owns decompose advance action dispatch helper (preview/confirm/bootstrap/execute/tick branch execution).
  - `services/workflow_decompose_support.py` owns decompose aggregate-status/routing-decision helper logic.
  - `services/workflow_api_handlers.py` owns API handler adapter layer for decompose/orchestrate/execute runtime dispatch.
  - `services/runtime_bootstrap.py` owns runtime/service assembly for scheduler/engine/dispatch/api-handler composition.
  - `services/workflow_orchestration_runtime.py` owns orchestrate/recover runtime lifecycle.
  - `services/workflow_orchestration_runtime_policy.py` owns orchestration strategy-profile and recovery request/response policy helpers.
  - `services/workflow_orchestration_support.py` owns orchestration decision/telemetry/record helper logic.
  - `services/workflow_orchestration_support_decision.py` owns orchestration recovery scoring and decision-report assembly helpers.
  - `services/workflow_orchestration_support_summary.py` owns decomposition summary, telemetry snapshot, and recovery-action resolve helpers.
  - `services/metrics_authorization.py` owns metrics policy/rollback authorization helper logic.
  - `services/metrics_alert_policy_store_rollback.py` owns rollback-approval/purge-audit persistence and timestamp filtering helpers.
  - `services/metrics_alert_policy_store_policy.py` owns metrics-alert policy normalize/query/statistics and purge-computation helpers.
  - `services/metrics_alert_policy_store_io.py` owns metrics-alert policy/verify/audit file I/O helpers.
  - `services/metrics_alert_policy_store_verify.py` owns verify-policy-registry normalize/serialize helpers.
  - `services/workflow_scheduler_indexes.py` owns scheduler index rebuild helpers (run/workitem/discussion/gate/artifact views).
  - `services/workflow_scheduler_dependencies.py` owns scheduler dependency validation and pending-ready selection helpers.
  - `services/workflow_scheduler_status.py` owns workflow-run status derivation and scheduler metrics aggregation helpers.
  - `services/workflow_engine_bootstrap_helpers.py` owns workflow-engine bootstrap helpers (module/task-package normalize + metadata/terminal derivation).
  - `services/workflow_engine_runtime_helpers.py` owns workflow-engine runtime helpers (execution text/summary + reflow graph/artifact helpers).
  - `services/command_orchestration_policy.py` owns `/orchestrate` command-intent parse + policy execution.
  - orchestrate command policy includes clarification-first ambiguity gate (`tbd/todo/???/待定`) to prevent requirement guessing.
  - orchestrate command policy supports `--restart-latest-canceled=true` to restart latest canceled run from task context.
  - orchestrate command policy supports configurable auto-restart policy (`off|auto_if_no_requirements|always`), explicit flag has highest priority.
  - `services/command_dispatch.py` owns command dispatch short-circuit/routing/metadata/action execution adapter logic.
  - runtime bootstrap and API routers resolve scheduler/engine/action through runtime providers to keep monkeypatch/test runtime state consistent.
  - workflow core router resolves scheduler/engine via runtime providers to keep test/runtime state consistent.
  - `services/dev_routing_matrix.py` handles developer specialization routing policy.

3. Action Layer (Execution)
- Executes role work items.
- Supports provider routing and discussion escalation.
- Service modularization:
  - `services/runtime_execution.py` handles execution decision and response contracts.
  - `services/agent_rules_registry_loader.py` loads shared role->executor mapping from capability registry (with fallback).
  - `services/llm_executor.py` handles llm routing/executor assembly.
  - `services/llm_executor_runtime_helpers.py` owns llm http transport/response parse/route select helpers.
  - `services/llm_executor_exceptions.py` owns llm configuration/runtime exception types.

4. Subproject Workspace (`project/<key>/`)
- Generated and managed by main project automation.
- Subproject business code is disposable/rebuildable.
- Requirement file is source-of-truth input.

5. Reusable Capability Plane (Agent / MCP / Skills)
- Shared capability packaging to avoid cross-project duplicate implementation.
- Type boundary:
  - Agent: decision + orchestration behavior.
  - MCP: tool/protocol bridge with strict permission boundary.
  - Skills: reusable workflow template with prompts/scripts/references.

## V2 Design Principles

- Requirement-first: every run starts from requirement file.
- Rebuildable subproject: generated artifacts can be reset and recreated.
- Strict outputs: every run writes JSON reports.
- Token-aware operation: small prompts, bounded context, role-specific inputs.
- Plan -> Implement -> Check -> Docs is mandatory order.
- Standard Agent alignment: action execution responses follow ReAct loop contract (`plan/act/observe/final`) via structured `agent_trace`.

## Standard Agent Contract (ReAct)

`ActionExecuteResponse` keeps stable core fields (`status`, `summary`, `agent`, `trace_id`) and adds:
- `agent_trace.standard`: `ReAct`
- `agent_trace.version`: protocol version
- `agent_trace.loop_state`: lifecycle state
- `agent_trace.steps[]`: ordered step list (`index`, `phase`, `content`, optional `tool`, `status`)
- `agent_trace.final_decision`: terminal decision
- `metadata.agent_standard`: protocol metadata (`protocol`, `version`, `trace_schema`)

Notes:
- Do not expose raw chain-of-thought; `steps[].content` is concise operational trace.
- If model output does not include `agent_trace`, Action Layer synthesizes a compliant default trace.
- Canonical spec: `docs/STANDARD_AGENT_REACT.md`
- Canonical schema: `control_center/capabilities/protocols/react_trace_v1.schema.json`

## V2 Pipeline

1. Read requirement file.
2. Build orchestration intent (modules, strategy, limits).
3. Generate subproject scaffold.
4. Execute standalone subproject flow.
5. Run acceptance checks via control-center API check entry.
6. Write V2 run report.

## Boundaries

- Main project owns orchestration, quality gates, and lifecycle commands.
- Subproject owns generated business implementation only.
- User gives goal/constraints; AI delivers end-to-end execution.

## Capability Packaging Contract

Each reusable capability package follows one manifest contract:
- identity: `id`, `type`, `version`, `owner`
- execution: `entry`, `runtime`, `timeouts`
- schema: `input_schema`, `output_schema`
- failure: `error_contract` (`code`, `retryable`, `recovery_hint`)
- permission: filesystem/network/env/tool scopes
- observe: required events/metrics fields
- compatibility: minimal wherecode version and platform constraints

Registration flow (single path for built-in and third-party):
1. Submit package manifest.
2. Validate schema + permission contract.
3. Register to capability registry.
4. Dry-run in sandbox.
5. Promote to active and append audit log.
