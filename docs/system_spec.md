# System Spec (v3)

Updated: 2026-03-03

## 1) Architecture

- `Command Center`: mobile/web UI for project/task/command operations.
- `Control Center`: orchestration, gate checks, policy, persistence, metrics.
- `Action Layer`: role agent execution endpoint (`/execute`) with profile isolation.

Main execution mode:
- HTTP async (`POST` accept -> `GET` poll).
- Role workflow (`workitem`) managed by scheduler + engine.

## 2) Role model

Roles:
- `chief-architect`
- `module-dev`
- `doc-manager`
- `qa-test`
- `security-review`
- `acceptance`
- `release-manager`
- `integration-test` (global test stage)

Module stage order:
- `module-dev -> doc-manager -> qa-test -> security-review`

Global stage order:
- `integration-test -> acceptance -> release-manager`

## 3) Context isolation

- Role profile path: `action_layer/agents/<role>/agent.md`
- SubAgent can read only its own profile.
- Cross-role profile read is rejected and audited.

## 4) Workflow entities

Base hierarchy:
- `Project -> Task -> Command`

v3 orchestration entities:
- `WorkflowRun`
- `WorkItem`
- `DiscussionSession`
- `GateCheck`
- `Artifact`

Key relation rules:
- `WorkItem.depends_on` must point to existing workitems in same run.
- `GateCheck` and `DiscussionSession` bind to one `WorkItem`.
- `Artifact` owner is workflow run or workitem.

## 5) State machine (current)

`WorkflowRunStatus`:
- `planning`, `running`, `waiting_approval`, `blocked`, `failed`, `succeeded`, `canceled`

`WorkItemStatus`:
- `pending`, `ready`, `running`, `needs_discussion`, `waiting_approval`, `failed`, `succeeded`, `skipped`

`DiscussionStatus`:
- `open`, `resolved`, `exhausted`, `timeout`

`GateStatus`:
- `passed`, `failed`

## 6) Gate and reflow rules

- Doc/Test/Security gates run by role:
  - `doc-manager` -> doc gate
  - `qa-test` / `integration-test` -> test gate
  - `security-review` -> security gate
- Gate fail on module stage can trigger module reflow.
- Reflow has max attempts (`WHERECODE_MAX_MODULE_REFLOWS`).
- Release stage can require approval (`WHERECODE_RELEASE_APPROVAL_REQUIRED=true`).

## 7) Discussion rules

- Each workitem has `discussion_budget` and `discussion_timeout_seconds`.
- Exceed budget -> mark failed (`discussion_budget_exhausted`).
- Duplicate fingerprint without new context -> loop detected -> fail.
- Resolve discussion sets workitem back to `ready`.

## 8) Persistence and observability

- Backend: `memory` or `sqlite` (`WHERECODE_STATE_BACKEND`).
- SQLite persists run/workitem/discussion/gate/artifact.
- Metrics endpoints:
  - `/metrics/summary`
  - `/metrics/workflows`
- Policy/governance endpoints:
  - `/metrics/workflows/alert-policy*`
  - `/metrics/workflows/alert-policy/verify-policy*`
  - rollback approval + purge audit endpoints.
