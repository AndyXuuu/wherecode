# Scripts (V2)

## Primary Entry

- `stationctl.sh`
  - service ops: `install|dev|start|stop|status`
  - orchestration: `main-orchestrate|plan-autopilot|v2-run|v2-replay|v2-report|orchestrate-policy`
  - checks: `check quick|main|v2|release|ops|evolve`

## Main Flow

- `main_orchestrate.sh`
  - main project orchestrate template
  - writes latest summary through mb3 seed path

- `plan_autopilot.sh`
  - continuous PLAN executor for `Current Sprint (Ordered)`
  - picks first `planned|doing` task, runs orchestrate flow, updates PLAN status/log
  - done gate => command `success` + orchestration status `executed|prepared`
  - default requires terminal `next_action` (not `review_results`): `--require-final-next-action true`
  - optional verify gate: `--verify-cmd "<command>"`
  - failure => blocker log + retry (supports forever retry)
  - strict gate preset: `--strict --max-retries 2` (one repair retry then stop)
  - skip-next preset: `--non-strict --max-retries 2` (one repair retry then continue)

- `v2_run.sh`
  - requirement-driven v2 pipeline
  - canonical requirement input: `project/requirements/<subproject>.md`
  - runtime snapshot: `project/<subproject>/REQUIREMENTS.md`
  - report diagnosis includes `failure_taxonomy`, `retry_hints`, `next_commands`
  - mode:
    - `plan`: dry-run orchestration plan
    - `build`: generate + run + acceptance
  - workflow-mode:
    - `test` (default): execute full build flow and print/log all operations
    - `dev`: execute one stage per run (`generate -> standalone -> acceptance`)
    - supports `--state-path`, `--ops-log-path`, `--reset-dev-state`
    - prints `workflow_next_command` in dev mode for copy-run continuation
  - outputs:
    - `docs/v2_reports/<timestamp>-<subproject>-v2-run.json`
    - `docs/v2_reports/latest_<subproject>_v2_run.json`

- `v2_replay.sh`
  - replay using fixed requirement snapshot: `project/<subproject>/REQUIREMENTS.md`
  - can inherit module/runtime params from latest V2 report input section
  - supports `--source-report <path>` to replay from selected historical run metadata
  - entry for deterministic re-run of the same requirement baseline

- `v2_report_summary.sh`
  - human-readable summary for latest or selected V2 report
  - supports remote API mode: `--api --control-url <url> [--token <token>]`
  - supports deterministic lookup by report id: `--report-id <report_id>`
  - supports deterministic lookup by workflow run id: `--run-id <workflow_run_id>`
  - prints final status + diagnosis taxonomy + retry hints + next commands
  - supports `--compact` for mobile-friendly short output
  - supports `--json` for structured output (includes `compact` + `prioritized_actions` + `primary_action`)
  - supports action filtering via `--min-score` and `--action-type`
  - prioritized actions carry stable `action_id`, numeric `score`, and execution metadata (`runbook_ref`, `can_auto_execute`, `requires_confirmation`, `estimated_cost`)

## Existing Pipeline Core

- `go8_subproject_full_cycle.sh`
  - full automatic subproject cycle
  - supports `--workflow-mode test|dev`
  - writes operation log: `project/<subproject>/reports/<stamp>-workflow-ops.jsonl`
  - writes stage cursor: `project/<subproject>/reports/workflow_state.json`
- `go7_subproject_generate.sh`
  - requirement-driven subproject generation
- `go6_subproject_autoevolve.sh`
  - compatibility wrapper to full-cycle path

## Check Entry

- `check_all.sh`
  - API gateway for unified check entry (`POST /ops/checks/runs`)
  - sync mode (default): wait for terminal status and return non-zero on failure
  - async mode: `--async` to create run and return immediately
  - supports remote execution visibility via `control_center` API

- `check_all_local.sh`
  - local executor used by control-center check API
  - contains real check implementation per scope
  - scopes: `quick|dev|release|ops|evolve|main|v2|all|backend|backend-quick|backend-full|llm-check|frontend|projects`
  - `v2` scope also runs capability contract gate + developer routing matrix gate + `v2_gate` report/status gate

- `v2_gate.sh`
  - validates latest/report payload structure and terminal status for V2 runs
  - verifies benchmark targets, run/input sections, and build-mode full-cycle status
  - default target: `docs/v2_reports/latest_<subproject>_v2_run.json`

- `capability_contract_check.py`
  - validates capability manifest/registry contract
  - default: validate `control_center/capabilities/registry.json`
  - optional: `--manifest <path>` (repeatable)

- `dev_routing_matrix_check.py`
  - validates `control_center/capabilities/dev_routing_matrix.json`
  - checks required fields, rule shape, and duplicate IDs
