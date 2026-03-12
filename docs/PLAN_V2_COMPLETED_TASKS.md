# WhereCode V2 Completed Tasks

Updated: 2026-03-12

## Group A: Reset / Baseline / Planning

- V2-T1 clear docs, keep architecture + operation notes only
- V2-T2 clear subproject code, keep requirement only
- V2-T3 add v2 orchestrate script and config
- V2-T4 wire stationctl/check and run validation
- V2-T5 extend benchmark target set to include Oh My OpenCode
- V2-T6 write v2 project planning document
- V2-T7 write Chinese V2 project planning document
- V2-T8 add control-center API for check runs
- V2-T9 switch check_all/stationctl check entry to API call
- V2-T10 update docs for remote progress/report query

## Group B: Capability Packaging

- V2-T14 build common capability catalog and packaging boundary (Agent vs MCP vs Skills)
- V2-T15 define packaging contracts (input/output/error/permission/version)
- V2-T16 add reusable templates and registration flow for third-party extension
- V2-T17 integrate capability contract check into v2 check scope
- V2-T18 restore root README mission statement (ultimate goal section)

## Group C: Dev Routing / Orchestration Policy

- V2-T20 define developer specialization routing matrix (frontend/backend/language/task/risk)
- V2-T21 integrate dev routing matrix into chief orchestration path (auto route by domain/stack/task/risk)
- V2-T22 expose routing decision query API for workflow runs (mobile visibility)
- V2-T23 refactor control-center routing logic into dedicated service module
- V2-T24 refactor action-layer execution decision logic into dedicated service module

## Group D: API Split / Runtime Service Extraction

- V2-T25 split workflow core API endpoints into dedicated router module
- V2-T26 refactor ops check runtime and APIs into dedicated service/router modules
- V2-T27 split workflow execute and discussion APIs into dedicated router module
- V2-T28 split workflow orchestration APIs into dedicated router module
- V2-T29 split project/task/command hierarchy APIs into dedicated router module
- V2-T30 split metrics and metrics-policy APIs into dedicated router module
- V2-T31 split agent-routing APIs into dedicated router module
- V2-T32 split action-layer proxy APIs into dedicated router module
- V2-T33 extract workflow execute runtime implementation into dedicated service module
- V2-T34 extract workflow orchestration/recovery runtime implementation into dedicated service module
- V2-T35 extract command orchestrate policy runtime from entrypoint into dedicated service module
- V2-T36 extract decompose advance/confirm/status runtime from entrypoint into dedicated service module
- V2-T37 extract decompose bootstrap generation/runtime from entrypoint into dedicated service module
- V2-T38 add focused unit tests for workflow decompose runtime service
- V2-T39 extract workflow orchestrate decision/telemetry support helpers from entrypoint into dedicated support service
- V2-T40 extract workflow decompose aggregate/routing helpers from entrypoint into dedicated support service
- V2-T41 extract workflow decompose preview/cache helpers from entrypoint into dedicated support service
- V2-T42 extract metrics authorization helpers from entrypoint into dedicated support service
- V2-T43 add focused unit tests for metrics authorization support service
- V2-T44 extract chief decompose prompt/coverage/mapping/task-package helpers from entrypoint into dedicated support service
- V2-T45 extract control-center app wiring/bootstrap from entrypoint into dedicated module
- V2-T46 extract workflow API handler adapter layer from entrypoint into dedicated service module
- V2-T47 extract command dispatch routing/metadata execution logic from entrypoint into dedicated service module
- V2-T48 extract control-center env/config bootstrap parsing from entrypoint into dedicated service module
- V2-T49 extract control-center runtime/service assembly from entrypoint into dedicated bootstrap module

## Group E: Large File Reduction / Service Internal Split

- V2-T50 split metrics alert policy store into dedicated helper modules (rollback + verify-registry utils)
- V2-T51 split workflow decompose runtime into dedicated helper modules (validation + metadata/pending extraction)
- V2-T52 split workflow decompose helpers into dedicated helper modules (coverage/mapping + task-package utils)
- V2-T53 split workflow scheduler into dedicated helper modules (queue selection + group dependency/policy utils)
- V2-T54 split workflow engine into dedicated helper modules (execution loop + discussion/retry policy utils)
- V2-T55 split workflow orchestration runtime into dedicated helper modules (policy/decision-report + telemetry persistence utils)
- V2-T56 split workflow orchestration support into dedicated helper modules (decomposition summary + recovery scoring/telemetry utils)
- V2-T57 split workflow decompose runtime into dedicated helper modules (chief execution + confirmation/advance policy utils)
- V2-T58 split metrics alert policy store into dedicated helper modules (policy normalize/query + alert statistics utils)
- V2-T59 split action-layer llm executor into dedicated helper modules (provider config + prompt/response adaptation utils)
- V2-T60 one-shot large-file reduction pack (>500 production files)
- V2-T60-A reduce `metrics_alert_policy_store.py` below 500 by extracting policy/verify/audit I/O helpers
- V2-T60-B reduce `llm_executor.py` below 500 by extracting route-target validation helper

## Group F: Context Isolation / Memory Namespace Baseline

- V2-T12 implement context isolation envelope (main/project/shared)
- V2-T13 design memory namespace (shared + isolated) and access policy

## Group G: Role Rules Registry / Clarification-First Gate

- V2-T11 define role model and agent rules registry (main/subproject)
- V2-T19 enforce autonomous execution + interrupt control + clarification-first policy (no requirement guessing)
- V2-T11-A implement file-backed agent rules registry (main/subproject scopes) + query API
- V2-T11-B make Action Layer load shared agent rules registry for runtime role->executor mapping
- V2-T19-A add clarification-first gate for orchestrate command (ambiguous requirement markers)
- V2-T19-B add workflow run interrupt API and cancellation-safe execution loop/status refresh
- V2-T19-C add workflow run restart path and canceled-run recovery routing (orchestrate/recover aware)
- V2-T19-D add command-layer restart entry (`/orchestrate --restart-latest-canceled`) and task-state sync
- V2-T19-E add configurable auto-restart strategy for canceled latest run in command orchestrate policy
- V2-T19-F expose command orchestrate restart policy via runtime config API for remote clients
- V2-T19-G add `stationctl orchestrate-policy` command for restart-policy remote/local query
- V2-T19-H add `v2_gate` report/status validation and integrate into `check_all v2`
- V2-T19-I add one-command replay flow from requirement snapshot (`stationctl v2-replay`)
- V2-T19-J add V2 report diagnosis (`failure_taxonomy` + `retry_hints`) and validate through `v2_gate`
- V2-T19-K add historical report source replay (`v2-replay --source-report`) for deterministic rerun
- V2-T19-L add `stationctl v2-report` summary command for latest/history diagnosis and retry actions
- V2-T19-M expose V2 report summary API (`GET /reports/v2/summary`) for remote/mobile diagnosis visibility
- V2-T19-N add compact mobile summary and prioritized recovery actions for V2 report API/CLI
- V2-T19-O standardize alert priority and action suggestion contract for V2 summary (stable action id + score + primary action)
- V2-T19-P add action execution guidance metadata + summary action filters (`min_score`, `action_type`) for V2 report API/CLI
- V2-T19-Q add remote API mode for `stationctl v2-report` (control-url/token + same filters/output contract)
- V2-T19-R add `run_id` lookup for V2 report summary API/CLI (deterministic report query by workflow run id)
- V2-T19-S add `report_id` lookup + response field for V2 report summary API/CLI (deterministic query when run_id missing)

## Group H: Standard Agent Protocol Alignment

- V2-T61 align to standard agent protocol (ReAct loop contract: plan/act/observe/final with structured trace in action execution response)
- V2-T62 define ReAct standard explicitly (normative spec + machine-readable schema + runtime schema reference)
- V2-T63 define workflow execution mode (`test|dev`): full operation/file logging in test mode, one-stage progression in dev mode
- V2-T64 add workflow next-command hints: print copy-ready next step in dev mode and persist in run reports
- V2-T65 produce delivery-test package: release-level checks + V2 flow acceptance checklist + evidence links

## Group I: Archive Batch 2026-03-12 (Current Sprint Cleanup)

- V2-T66 produce benchmark function-gap matrix (OpenClaw/OpenCode/Oh My OpenCode vs WhereCode) with priority backlog
- V2-T67 implement capability lifecycle minimal APIs (`list/install/enable/disable/uninstall`)
- V2-T68 implement MCP runtime adapter (`load/start/health/invoke/stop`)
- V2-T69 add capability audit trail + permission baseline checks
- V2-T70 unify workflow state persistence for run/stage/checkpoint
- V2-T71 finalize resume/restart command + API closure
- V2-T72 standardize failure taxonomy + retry hints in report API
- V2-T73 add run timeline API (stage/status/duration)
- V2-T74 add artifact/report index query API by run id
- V2-T75 add compact mobile summary API contract
- V2-T76 run stock-sentiment autopilot generation drill from requirement
- V2-T77 run main/v2 regression check package and publish evidence
- V2-T78 finalize docs for architecture/operations/acceptance evidence
- V2-T79 add plan-autopilot command to execute PLAN tasks continuously until completion
- V2-T80 add repo skill entry so Codex slash command can trigger plan-autopilot
- V2-T81 add `plan-autopilot-strict` skill: fail-stop gate mode with one repair attempt or optional skip-next mode

## Group J: Plan Autopilot Completion Gate Hardening

- V2-T84 harden `plan-autopilot` done gate (require execution evidence and block false-positive completion)
