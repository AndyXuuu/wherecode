# 2026-03-01 K11 Alert Policy API

## Goal

- Expose metrics alert policy as runtime APIs instead of static-file-only updates.
- Add audit visibility for alert policy changes.

## Plan updates

- Updated `PLAN.md`:
  - added Sprint-K11 (`K11-T1/T2/T3`)
  - recorded started/completed entries
- Updated `docs/v3_task_board.md`:
  - added K11 tasks and marked all `done`

## Changes

1. New policy store service
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Provides:
     - policy load/save
     - defaults and normalization
     - audit append/load
     - recent-audit query

2. New alert policy APIs
   - File: `control_center/main.py`
   - Added endpoints:
     - `GET /metrics/workflows/alert-policy`
     - `PUT /metrics/workflows/alert-policy`
     - `GET /metrics/workflows/alert-policy/audits`
   - Added runtime env support:
     - `WHERECODE_METRICS_ALERT_POLICY_FILE`
     - `WHERECODE_METRICS_ALERT_AUDIT_FILE`

3. API models and exports
   - Files:
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
     - `control_center/services/__init__.py`
   - Added request/response/audit schemas for alert policy APIs.

4. Tests
   - New: `tests/unit/test_v3_metrics_alert_policy_api.py`
   - Updated:
     - `tests/unit/test_openapi_contract.py`
     - `tests/conftest.py` (isolated temp policy store per test)
   - OpenAPI snapshot refreshed:
     - `tests/snapshots/openapi.snapshot.json`

5. Ops docs
   - Updated:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
   - Added API usage examples for querying/updating policy and listing audits.

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `104 passed`

## Risk / follow-up

- Current update endpoint relies on existing token auth and has no fine-grained role control yet.
- Next step: add role-based permission checks and update audit fields with caller identity binding.
