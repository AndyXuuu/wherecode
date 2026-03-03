# Change Report: K1-T4 workflow scheduler

Date: 2026-03-01

## 1. Goal

- Implement K1-T4 from v3 backlog.
- Add minimal DAG ready-queue scheduler (`2 parallel + 1 join`).

## 2. Plan update

- Updated `PLAN.md`:
  - marked K1-T4 started
  - marked K1-T4 completed with verification commands
- Updated `docs/v3_task_board.md`:
  - changed K1-T4 status from `doing` to `done`

## 3. Implementation

- Added `control_center/services/workflow_scheduler.py`:
  - `WorkflowScheduler` in-memory scheduler
  - run creation and retrieval
  - workitem insertion with dependency validation
  - `tick()` to move `pending -> ready` when dependencies are satisfied
  - status transitions:
    - `start_workitem`: `ready -> running`
    - `complete_workitem`: `running/ready -> succeeded|failed`
  - run status aggregation:
    - any failed -> `failed`
    - all succeeded/skipped -> `succeeded`
    - otherwise -> `running` (or `planning` if empty)
- Updated `control_center/services/__init__.py` exports.
- Added `tests/unit/test_workflow_scheduler.py`:
  - parallel + join DAG case
  - unknown dependency rejection
  - run failure aggregation
  - run success aggregation
  - start requires ready status

## 4. Verification

- `control_center/.venv/bin/pytest -q tests/unit/test_workflow_scheduler.py`
  - result: `5 passed`
- `control_center/.venv/bin/pytest -q tests/unit`
  - result: `75 passed`

## 5. Risks / follow-up

- Scheduler is service-level only; not exposed through v3 API yet.
- Next task: K1-T5 (`/v3/workflows/*` API contracts and endpoints).
