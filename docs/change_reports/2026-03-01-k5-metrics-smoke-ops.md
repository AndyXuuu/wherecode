# Change Report: K5 metrics, smoke, and ops docs

Date: 2026-03-01

## 1. Goal

- Complete M5 backlog items in one pass:
  - `K5-T1` workflow metrics endpoint
  - `K5-T2` v3 smoke script
  - `K5-T3` ops documentation updates

## 2. Plan update

- Updated `PLAN.md` with K5 start/completion records.
- Updated `docs/v3_task_board.md`:
  - `K5-T1` -> `done`
  - `K5-T2` -> `done`
  - `K5-T3` -> `done`

## 3. Implementation

- Metrics:
  - Added `WorkflowMetricsResponse` model
  - Added scheduler aggregation `get_metrics()` for:
    - run status counts
    - workitem status counts
    - gate status counts
    - artifact type counts
  - Added API endpoint:
    - `GET /metrics/workflows`
- Approval/artifact flow hardening (covered during K4/K5 stabilization):
  - Added `ApproveWorkItemRequest`
  - Execute response now includes waiting approval counts/ids
  - Added run artifacts endpoint:
    - `GET /v3/workflows/runs/{run_id}/artifacts`
  - Added workitem approval endpoint:
    - `POST /v3/workflows/workitems/{workitem_id}/approve`
- Smoke tooling:
  - Added `scripts/v3_workflow_smoke.sh`
  - Covers:
    - run creation
    - bootstrap
    - execute
    - discussion resolve branch
    - approval branch
    - artifact verification
- Ops docs:
  - Updated `docs/runbook.md` with:
    - `metrics/workflows`
    - `v3_workflow_smoke.sh`
    - discussion and approval operational commands
  - Updated `docs/troubleshooting.md` with v3 blocked/waiting_approval/reflow cases

## 4. Verification

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_metrics.py tests/unit/test_v3_workflow_engine_api.py tests/unit/test_workflow_scheduler.py tests/unit/test_workflow_engine.py tests/unit/test_openapi_contract.py`
- Full:
  - `control_center/.venv/bin/python scripts/update_openapi_snapshot.py`
  - `control_center/.venv/bin/pytest -q`
  - result: `101 passed`

## 5. Risks / follow-up

- v3 state is still in-memory only (restart will clear run/workitem/gate/artifact/discussion data).
- Smoke script assumes `python3` is available for JSON parsing.
- Future production hardening should add persistent storage and alerting integrations.
