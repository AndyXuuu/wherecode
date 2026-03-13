# WhereCode V3 Project Plan

Updated: 2026-03-13

## 1. Goal

Build V3 as a control plane for autonomous software delivery:

- Main project focuses on orchestration, gates, state, evidence, and APIs.
- OpenCode / OhMyOpenCode focus on execution (code generation + edits).
- User provides goal/suggestion only; system executes end-to-end.

## 2. Architecture (V3 Baseline)

### 2.1 Layers

- Control Plane (WhereCode main):
  - requirement analysis
  - proactive clarification (no-guess gate)
  - SDD stage orchestration
  - acceptance/done gate
  - report/evidence API
- Execution Plane (External engines):
  - Single OpenCode adapter
  - Strategy routing: `native|ohmy`
  - role policy source: `.agents/policies/role_routing.v3.json`
- Artifact Plane:
  - run state
  - stage artifacts
  - evidence reports

### 2.2 Workflow State Model

- `draft`
- `clarifying`
- `planned`
- `executing`
- `verifying`
- `accepted`
- `blocked`

### 2.3 SDD Stage Model

Required stage order:

`intent -> spec -> design -> tasks -> implement -> verify -> accept`

Each stage must produce artifacts; otherwise next stage is blocked.

## 3. Milestones

| ID | Target | Scope | Exit Gate |
| --- | --- | --- | --- |
| V3-M1 | Week 1 | overlap de-dup baseline | overlap audit published; duplicated execution scope marked delegated |
| V3-M2 | Week 2 | adapter-first integration | single OpenCode adapter callable from control-plane with unified result schema and `native|ohmy` strategy |
| V3-M3 | Week 3 | clarification gate | unresolved ambiguity forces `clarifying/awaiting_clarification` and blocks implementation |
| V3-M4 | Week 4 | SDD gate chain | full `intent -> spec -> design -> tasks -> implement -> verify -> accept` chain enforced by artifacts |
| V3-M5 | Week 5 | acceptance evidence gate | terminal done requires evidence package completeness + required checks |
| V3-M6 | Week 6 | remote timeline API | device-agnostic API returns run timeline, artifacts, report, and next action |

## 4. V3 Backlog (Priority)

1. De-dup execution responsibilities:
   - keep execution runtime in OpenCode/OhMy
   - shrink action-layer into adapter gateway only
2. Define V3 run contract:
   - add `requirement_status`, `clarification_rounds`, `assumption_used`
   - add stage-level artifact checklist
3. Implement external executor adapters:
   - `executor/opencode` only
   - strategy profiles: `native|ohmy`
4. Implement proactive clarification service:
   - ambiguity detector
   - ask/answer loop limits
   - block policy when unresolved
5. Implement SDD orchestrator:
   - fixed stage transitions
   - transition guard + recovery hint
6. Harden done gate:
   - no `review_results` as terminal done signal
   - require explicit terminal stage + evidence completeness
7. Add acceptance APIs:
   - `/v3/runs/{id}/timeline`
   - `/v3/runs/{id}/artifacts`
   - `/v3/runs/{id}/report`

## 5. Acceptance Criteria (V3)

- Can create one run from requirement and complete full SDD chain.
- If requirement is ambiguous, run must stop in `clarifying`.
- `accepted` is reachable only with required evidence artifacts.
- Switching executor target (OpenCode / OhMy) does not change control-plane contract.
- Mobile/API can read progress and final report for each run.

## 6. Defaults

- Single-host deployment first (no distributed scheduler in V3 baseline).
- No role permission matrix expansion in V3 baseline.
- Hard cut V3 main path: remove V2 execution entry commands from `stationctl`.

## 7. Engineering Layout Reference

- `docs/V3_ENGINEERING_LAYOUT.md`
- `docs/V3_OVERLAP_AUDIT.md`
