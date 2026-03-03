# 2026-03-01 K6 Persistence Hardening

## Goal

- Complete K6 persistence hardening for v3 orchestration:
  - scheduler SQLite persistence + restore
  - restart recovery tests
  - ops documentation updates

## Plan updates

- Updated `PLAN.md` with K6 resumed/completed records.
- Updated `docs/v3_task_board.md` statuses:
  - `K6-T1` done
  - `K6-T2` done
  - `K6-T3` done

## Code changes

1. Scheduler persistence and restore
   - File: `control_center/services/workflow_scheduler.py`
   - Added SQLite load path for:
     - `workflow_run`
     - `workitem`
     - `discussion_session`
     - `gate_check`
     - `artifact`
   - Added index rebuild logic for run/workitem/discussion/gate/artifact links.
   - Added persistence hooks on state mutation paths:
     - run creation/status refresh
     - workitem lifecycle transitions
     - discussion create/resolve/timeout/exhausted
     - gate/artifact creation
     - dependency update / skip
   - Added `persist_run(run_id)` for run metadata persistence from engine layer.

2. Main app wiring
   - File: `control_center/main.py`
   - `WorkflowScheduler` now reuses configured `state_store` when `WHERECODE_STATE_BACKEND=sqlite`.

3. Engine metadata persistence bridge
   - File: `control_center/services/workflow_engine.py`
   - Persist run after bootstrap metadata write and module reflow metadata updates.

## Tests

- New file: `tests/unit/test_workflow_scheduler_persistence.py`
  - Verifies restart recovery for run/workitems/discussions/gates/artifacts.
  - Verifies restored indexes by checking gate attempt increment and artifact aggregation.

- Validation executed:
  - `control_center/.venv/bin/pytest -q tests/unit/test_workflow_scheduler.py tests/unit/test_workflow_scheduler_persistence.py tests/unit/test_workflow_engine.py tests/unit/test_v3_workflow_engine_api.py tests/unit/test_v3_workflow_metrics.py`
  - `control_center/.venv/bin/pytest -q tests/unit/test_openapi_contract.py`
  - `control_center/.venv/bin/pytest -q`

## Docs updates

- `docs/runbook.md`
  - Added explicit v3 persisted entity list and restart recovery validation steps.
- `docs/troubleshooting.md`
  - Added restart data-loss troubleshooting for v3 workflow records.

## Risk / follow-up

- Current persistence writes each entity update immediately; for high write volume, batching or transaction grouping may be needed in later optimization.
