# Operations V2

Updated: 2026-03-11

## Main Commands

```bash
bash scripts/stationctl.sh v2-run stock-sentiment
bash scripts/stationctl.sh v2-run stock-sentiment --mode plan
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode test
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode dev --reset-dev-state true
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode dev
bash scripts/stationctl.sh v2-replay stock-sentiment
bash scripts/stationctl.sh v2-replay --source-report docs/v2_reports/20260310T154715Z-stock-sentiment-v2-run.json --mode plan
bash scripts/stationctl.sh v2-report stock-sentiment
bash scripts/stationctl.sh v2-report stock-sentiment --compact
bash scripts/stationctl.sh v2-report --report-id 20260310T163704Z-stock-sentiment-v2-run
bash scripts/stationctl.sh v2-report --run-id wfr_20260310_example
bash scripts/stationctl.sh v2-report stock-sentiment --compact --min-score 60 --action-type rerun,validate
bash scripts/stationctl.sh v2-report stock-sentiment --api --control-url http://127.0.0.1:8000 --compact --min-score 60 --action-type validate
bash scripts/stationctl.sh v2-report --report docs/v2_reports/20260310T154715Z-stock-sentiment-v2-run.json
bash scripts/stationctl.sh orchestrate-policy
bash scripts/stationctl.sh plan-autopilot
bash scripts/stationctl.sh plan-autopilot --max-tasks 3
bash scripts/stationctl.sh plan-autopilot --strict --max-retries 2 --retry-interval 10
bash scripts/stationctl.sh plan-autopilot --non-strict --max-retries 2 --retry-interval 10
bash scripts/check_all.sh v2
bash scripts/check_all.sh main
```

Command-policy recover entry:

```bash
/orchestrate --restart-latest-canceled=true --execute=false
```

Auto-restart policy (env):
- `WHERECODE_COMMAND_ORCHESTRATE_RESTART_CANCELED_POLICY=off|auto_if_no_requirements|always`

Policy query helper:
- `stationctl orchestrate-policy [control_url]` -> calls `GET /config/command-orchestrate-policy`

## Unified Check API

Control Center provides API-driven check runs:

- `POST /ops/checks/runs`
- `GET /ops/checks/runs/{run_id}`
- `GET /ops/checks/latest?scope=<scope>`
- `GET /ops/checks/runs?scope=<scope>&run_status=<status>&limit=<n>`
- `GET /reports/v2/summary?subproject=<subproject>&report_id=<report_id>&run_id=<workflow_run_id>&compact=<bool>&max_actions=<n>&min_score=<0..100>&action_type=<type|csv>`
- `GET /v3/workflows/runs/{run_id}/routing-decisions`
- `POST /v3/workflows/runs/{run_id}/interrupt`
- `POST /v3/workflows/runs/{run_id}/restart`
- `GET /config/command-orchestrate-policy`
- `GET /agent-rules`
- `POST /agent-rules/reload`

Example:

```bash
curl -X POST "http://127.0.0.1:8000/ops/checks/runs" \
  -H "Content-Type: application/json" \
  -H "X-WhereCode-Token: change-me" \
  -d '{"scope":"v2","requested_by":"remote-device","wait_seconds":0}'
```

## Inputs

- Canonical requirement file:
  - `project/requirements/<subproject>.md`
- Runtime snapshot (auto-synced each run):
  - `project/<subproject>/REQUIREMENTS.md`

## Outputs

- V2 report:
  - `docs/v2_reports/<timestamp>-<subproject>-v2-run.json`
  - `docs/v2_reports/latest_<subproject>_v2_run.json`
  - workflow fields:
    - `run.workflow_mode`
    - `outputs.workflow_stage_executed`
    - `outputs.workflow_next_stage`
    - `outputs.workflow_complete`
    - `outputs.workflow_next_command`
    - `outputs.workflow_ops_log_path`
    - `outputs.workflow_state_path`
  - diagnosis fields: `diagnosis.failure_taxonomy`, `diagnosis.retry_hints`, `diagnosis.next_commands`
  - summary fields: `compact.alert_priority`, `compact.decision`, `prioritized_actions[].action_id`, `prioritized_actions[].score`, `prioritized_actions[].runbook_ref`, `prioritized_actions[].can_auto_execute`, `prioritized_actions[].requires_confirmation`, `prioritized_actions[].estimated_cost`, `primary_action`
- Check run reports:
  - `docs/v2_reports/check_runs/<run_id>.json`
- Subproject full-cycle report:
  - `project/<subproject>/reports/latest_full_cycle.json`
  - operation log: `project/<subproject>/reports/<stamp>-workflow-ops.jsonl`
  - stage cursor: `project/<subproject>/reports/workflow_state.json`

## Operator Flow

1. Maintain requirement file.
2. Run `stationctl v2-run`.
3. If you need step-by-step build, use `--workflow-mode dev` and rerun the same command for next stage.
4. If you need one-shot build, use `--workflow-mode test` (default).
5. Trigger checks through `check_all.sh` (API mode).
6. Track run status via `/ops/checks/runs/{run_id}` or `/ops/checks/latest`.
7. If needed, stop a running workflow via `/v3/workflows/runs/{run_id}/interrupt`.
8. Restart canceled run via `/v3/workflows/runs/{run_id}/restart` (new run id).
9. Or call `/v3/workflows/runs/{run_id}/orchestrate/recover` to execute recommended recovery action (includes `restart_workflow_run` for canceled run).
10. Read latest V2 report.
11. If status failed, follow recovery action in report and rerun.
12. For deterministic rerun from frozen snapshot, use `stationctl v2-replay <subproject>`.
13. For deterministic rerun from an exact historical run, use `stationctl v2-replay --source-report <report_path>`.
14. Use `stationctl v2-report` to inspect diagnosis/retry actions before rerun.
15. For remote/mobile diagnosis, use `stationctl v2-report --api --control-url <control_url>` (auth from `WHERECODE_TOKEN` or `--token`).
16. To query a deterministic report directly, use `stationctl v2-report --report-id <report_id>`.
17. To query a deterministic run result, use `stationctl v2-report --run-id <workflow_run_id>` (or API mode with the same option).

V2 local gate helper:
- `bash scripts/v2_gate.sh --subproject stock-sentiment`
- `check_all v2` runs `v2_gate.sh` automatically after `v2_run.sh --mode plan`.

## Gate

- `check_all v2` must pass before milestone advance.
- `check_all v2` includes capability contract gate (`scripts/capability_contract_check.py`).
- `check_all v2` includes developer routing matrix gate (`scripts/dev_routing_matrix_check.py`).
- `check_all v2` includes V2 report/status gate (`scripts/v2_gate.sh`).

## Reusable Capability Operation (V2-M10)

Common feature intake flow:
1. Classify capability type by boundary:
  - orchestration decision -> Agent
  - protocol/tool integration -> MCP
  - repeated workflow template -> Skills
2. Write package manifest with contract fields.
3. Validate schema/permission/cost budget.
4. Register into capability registry.
5. Dry-run in sandbox before active usage.

Current policy:
- New common feature is not merged directly into random modules.
- It must enter capability packaging flow first, then be referenced by orchestrator/subprojects.

## Developer Routing Matrix (Draft)

Machine-readable matrix:
- `control_center/capabilities/dev_routing_matrix.json`

Use fields for chief decomposition metadata:
- `domain`: `frontend|backend|data|infra|security`
- `stack`: framework/runtime tags
- `task_type`: `feature|bugfix|refactor|perf|migration|security-hardening`
- `language`: language tags
- `risk`: `normal|high`

Routing policy:
1. Match rules by priority (lower number first).
2. Select `target` role and capability package.
3. Execute `required_checks` before module close.
4. If `requires_human_confirmation=true`, block at milestone checkpoint.

Runtime behavior:
- chief `decompose-bootstrap` applies matrix to module task packages.
- routed metadata is attached into workitem metadata:
  - `task_routing_rule_id`
  - `task_routing_capability_id`
  - `task_routing_executor`
  - `task_routing_required_checks`
- workflow engine prefers `task_routing_executor` over static role->agent mapping.

Mobile query tip:
- poll `GET /v3/workflows/runs/{run_id}/routing-decisions` to render module-level route cards.

## Agent Rules Registry

- Registry file: `control_center/capabilities/agent_rules_registry.json`
- Scope model:
  - `main`: orchestration-level roles (e.g. chief-architect/release-manager)
  - `subproject`: implementation/testing/review roles
- Runtime query:
  - `GET /agent-rules`
  - `POST /agent-rules/reload`
- Action Layer role mapping uses same registry by default:
  - `ACTION_LAYER_AGENT_RULES_REGISTRY_FILE=control_center/capabilities/agent_rules_registry.json`
  - `ACTION_LAYER_AGENT_RULES_SCOPES=subproject,main`

## Clarification-First Gate

- `/orchestrate` command applies ambiguity markers gate before run creation.
- If requirement text contains `tbd/todo/???/待定/待补充/不确定`, command is blocked with clarification-required response.
- After clarifying requirements, rerun with `--clarified=true`.

## Standard Agent Trace

- `POST /action-layer/execute` response includes `agent_trace` (ReAct contract):
  - `standard`, `version`, `loop_state`, `steps`, `final_decision`, `truncated`
- Protocol metadata is in `metadata.agent_standard`.
- If upstream model does not return trace, Action Layer emits a default ReAct trace.
- Protocol spec: `docs/STANDARD_AGENT_REACT.md`
- Schema id: `wherecode://protocols/react_trace/v1`
- Schema file: `control_center/capabilities/protocols/react_trace_v1.schema.json`
