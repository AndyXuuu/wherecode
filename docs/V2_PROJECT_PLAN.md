# WhereCode V2 Project Plan

Updated: 2026-03-09

## 1. Objective

Build a programmer-first autonomous orchestration system.

V2 benchmark baseline:
- OpenClaw
- OpenCode
- Oh My OpenCode

Core target:
- One-command requirement-driven execution from main project.
- Rebuildable subproject lifecycle.
- Structured artifacts and milestone gates.

## 2. Scope

In scope:
- Main project orchestration flow (`plan` + `build`).
- Requirement-driven subproject generation and execution.
- Standardized reports (`docs/v2_reports/latest_*.json`).
- Command/check integration (`stationctl`, `check_all`).
- API-driven unified check entry for remote progress/query/report.

Out of scope (V2):
- Multi-host distributed scheduling.
- Cloud deployment platformization.
- Role-based permission model.

## 3. Architecture Baseline

- `command_center/`: input and run visibility.
- `control_center/`: decomposition/scheduling/gates/recovery/state.
- `action_layer/`: execution runtime/provider bridge.
- `project/requirements/*.md`: canonical requirement source.
- `project/<key>/`: rebuildable runtime workspace.

### 3.1 Reusable Capability Packaging Boundary (V2-M10)

| Type | Owns | Use When | Avoid When |
| --- | --- | --- | --- |
| Agent | role behavior, decomposition, workflow decision, acceptance strategy | needs reasoning and orchestration decisions | pure protocol bridge or static utility |
| MCP | protocol adapter to external/local tools (http/db/filesystem/browser) | needs stable tool access and permission boundary | task is mainly prompt/workflow logic |
| Skills | reusable workflow template (prompt + scripts + references) | repeated domain workflow with low integration cost | needs long-running stateful orchestration |

Selection rule:
1. External system/protocol first -> MCP.
2. Repeated workflow/prompt first -> Skills.
3. Cross-module/cross-role decision first -> Agent.

## 4. Delivery Phases

### P0 - Baseline Reset (done)
- Keep only core docs.
- Keep subproject requirement-only baseline.
- Ensure V2 command entry exists.

### P1 - V2 Core Flow (done)
- `scripts/v2_run.sh` supports `plan|build`.
- `stationctl.sh` supports `v2-run`.
- `check_all.sh` supports `v2` scope.

### P2 - Stability and Gates (next)
- Add V2 gate script (`scripts/v2_gate.sh`) for report/schema/status checks.
- Add deterministic smoke check for requirement parse and report fields.
- Add acceptance checklist for release readiness.

### P3 - Operator Experience (next)
- Improve run summary readability (short console + json details).
- Add failure taxonomy and retry hints in V2 report.
- Add one-command replay with fixed requirement snapshot.

### P4 - Reusable Capability Platform (next)
- Build common capability catalog (avoid duplicate implementation across projects).
- Introduce package contract for Agent/MCP/Skills.
- Introduce extension registration flow with trust tier and audit trail.

## 5. Milestones and Exit Gates

| Milestone | Scope | Exit Gate |
| --- | --- | --- |
| V2-M6 | planning package | this doc published and linked in docs index |
| V2-M7 | stability gate | `stationctl check v2` + `v2_gate.sh` pass |
| V2-M8 | operator-ready flow | plan/build/replay flow documented and reproducible |
| V2-M9 | release candidate | acceptance checklist green |
| V2-M10 | reusable capability packaging | boundary, contract, and extension flow documented and checkable |

## 6. Deliverables

Required artifacts:
- `docs/V2_PROJECT_PLAN.md`
- `docs/ARCHITECTURE_V2.md`
- `docs/OPERATIONS_V2.md`
- `docs/v2_reports/latest_<subproject>_v2_run.json`
- `control_center/capabilities/registry.json`
- `control_center/capabilities/capability_contract.schema.json`

Required commands:
- `bash scripts/stationctl.sh v2-run <subproject> --mode plan`
- `bash scripts/stationctl.sh v2-run <subproject> --mode build`
- `bash scripts/stationctl.sh check v2`

## 7. Working Cadence

Per task order (mandatory):
1. Update `PLAN.md`.
2. Implement.
3. Run checks.
4. Update docs.

Weekly execution loop:
- Requirement refine -> plan run -> build run -> gate check -> doc update.

## 8. Immediate Next Tasks

1. Publish capability catalog and Agent/MCP/Skills boundary.
2. Define package contract (input/output/error/permission/version/observe).
3. Add extension registration template and trust/audit checks.

## 9. Packaging Contract (Draft)

Every reusable capability package must provide:
- `id`, `type`, `version`, `owner`.
- `entry` and `runtime` metadata.
- `input_schema` and `output_schema` (json schema or ref).
- `error_contract` (code/retryable/recovery_hint).
- `permission_contract` (filesystem/network/env/tool scope).
- `cost_budget` (timeout/token/call budget).
- `observability` (events/metrics/log fields).
- `compatibility` (wherecode min version, platform limits).

Minimal lifecycle:
1. Build package manifest.
2. Validate contract.
3. Register to capability registry.
4. Dry-run in sandbox.
5. Promote to active with audit entry.
