# WhereCode V3 Project Plan

Updated: 2026-03-12

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
  - OpenCode adapter
  - OhMyOpenCode adapter
  - optional fallback adapter (local codex-compatible)
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
| V3-M1 | Week 1 | control-plane contract freeze | APIs/schemas for run state, stage artifacts, done gate locked |
| V3-M2 | Week 2 | OpenCode/OhMy adapters | both adapters callable by role routing with unified result schema |
| V3-M3 | Week 3 | clarification-first + no-guess | ambiguous requirement must enter `clarifying`; unresolved blocks implement |
| V3-M4 | Week 4 | SDD runtime loop | full SDD stage chain runnable with artifact gates |
| V3-M5 | Week 5 | acceptance gate hardening | done requires evidence package + required checks pass |
| V3-M6 | Week 6 | remote visibility | mobile/API can query run timeline, stage status, artifacts, and reports |

## 4. V3 Backlog (Priority)

1. Define V3 run contract:
   - add `requirement_status`, `clarification_rounds`, `assumption_used`
   - add stage-level artifact checklist
2. Implement external executor adapters:
   - `executor/opencode`
   - `executor/ohmyopencode`
3. Implement proactive clarification service:
   - ambiguity detector
   - ask/answer loop limits
   - block policy when unresolved
4. Implement SDD orchestrator:
   - fixed stage transitions
   - transition guard + recovery hint
5. Harden done gate:
   - no `review_results` as terminal done signal
   - require explicit terminal stage + evidence completeness
6. Add acceptance APIs:
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
- Keep compatibility with existing `stationctl` commands; add V3 commands incrementally.
