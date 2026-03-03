# Change Report: K2 discussion control (protocol + budget + loop guard)

Date: 2026-03-01

## 1. Goal

- Continue without phase-by-phase confirmation.
- Complete K2 backlog in one pass:
  - `K2-T1` needs_discussion protocol
  - `K2-T2` discussion budget + timeout
  - `K2-T3` loop guard via fingerprint

## 2. Plan update

- Updated `PLAN.md` with K2 start/completion records.
- Updated `docs/v3_task_board.md`:
  - `K2-T1` -> `done`
  - `K2-T2` -> `done`
  - `K2-T3` -> `done`

## 3. Implementation

- API/model changes:
  - Added `DiscussionPrompt`, `ResolveDiscussionRequest`
  - Extended `ActionExecuteResponse` with optional `discussion`
  - Extended `ExecuteWorkflowRunResponse` with discussion counters
  - Added exports in `control_center/models/__init__.py`
- Scheduler changes (`control_center/services/workflow_scheduler.py`):
  - Added discussion session storage/listing
  - Added `mark_needs_discussion` with budget and loop guard
  - Added `resolve_discussion` with timeout check
  - Added status helpers for discussion counts
  - Run status now supports `blocked` when any workitem is `needs_discussion`
- Engine changes (`control_center/services/workflow_engine.py`):
  - Handles `status=needs_discussion`
  - Opens discussion session with prompt payload
  - Respects discussion exhaustion as failed execution
  - Executes existing `ready` items before ticking pending items
  - Includes `discussion_resolved` signal in execution text for resume path
- Control Center API (`control_center/main.py`):
  - Added `GET /v3/workflows/workitems/{workitem_id}/discussions`
  - Added `POST /v3/workflows/workitems/{workitem_id}/discussion/resolve`
- Action Layer runtime (`action_layer/runtime.py`):
  - Added mock `needs_discussion` branch for `module-dev` + `needs-discussion` module
- Test action client (`tests/conftest.py`):
  - Added deterministic `needs_discussion` behavior for API tests
- Documentation:
  - Updated `docs/protocol.md` with discussion endpoints and semantics
  - Updated `docs/runbook.md` with blocked->resolve->resume commands

## 4. Verification

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_workflow_scheduler.py tests/unit/test_workflow_engine.py tests/unit/test_v3_workflow_engine_api.py tests/unit/test_openapi_contract.py`
- Full suite:
  - `control_center/.venv/bin/python scripts/update_openapi_snapshot.py`
  - `control_center/.venv/bin/pytest -q`
  - result: `91 passed`

## 5. Risks / follow-up

- Discussion resolution is currently explicit API-driven (no auto-decision policy yet).
- Workflow persistence for v3 entities is still in-memory.
- Next planned block is K3 gate executors (`doc/test/security`) with module reflow policy.
