# Change Report: K1-T5 workflow API

Date: 2026-03-01

## 1. Goal

- Implement K1-T5 from v3 backlog.
- Add `/v3/workflows/*` API endpoints for run/workitem orchestration.

## 2. Plan update

- Updated `PLAN.md`:
  - marked K1-T5 started
  - marked K1-T5 completed with verification commands
- Updated `docs/v3_task_board.md`:
  - changed K1-T5 status from `doing` to `done`

## 3. Implementation

- Updated `control_center/models/api.py`:
  - added `CreateWorkflowRunRequest`
  - added `CreateWorkItemRequest`
  - added `CompleteWorkItemRequest`
- Updated `control_center/models/__init__.py` exports.
- Updated `control_center/main.py`:
  - added `workflow_scheduler` service instance
  - added endpoints:
    - `POST /v3/workflows/runs`
    - `GET /v3/workflows/runs/{run_id}`
    - `POST /v3/workflows/runs/{run_id}/workitems`
    - `GET /v3/workflows/runs/{run_id}/workitems`
    - `POST /v3/workflows/runs/{run_id}/tick`
    - `POST /v3/workflows/workitems/{workitem_id}/start`
    - `POST /v3/workflows/workitems/{workitem_id}/complete`
  - added error mapping (`404`/`409`/`422`) for scheduler errors
- Added `tests/unit/test_v3_workflow_api.py`:
  - end-to-end API test for `2 parallel + 1 join`
  - unknown dependency test (`422`)
  - unknown run test (`404`)
  - invalid start-state test (`409`)
- Updated `tests/unit/test_openapi_contract.py`:
  - assert new v3 paths
  - assert new request schema fields/defaults
- Updated OpenAPI snapshot:
  - `tests/snapshots/openapi.snapshot.json`
- Updated `docs/protocol.md` head note with v3 API progress.

## 4. Verification

- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_api.py tests/unit/test_openapi_contract.py`
  - result: `7 passed`
- `control_center/.venv/bin/python scripts/update_openapi_snapshot.py`
  - snapshot updated successfully
- `control_center/.venv/bin/pytest -q tests/unit`
  - result: `79 passed`

## 5. Risks / follow-up

- API is in-memory only; no persistence for workflow runs/workitems yet.
- Scheduler/API now exist; next phase should implement K2 discussion budget protocol behavior (`needs_discussion` flow).
