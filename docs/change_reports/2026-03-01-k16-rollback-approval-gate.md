# 2026-03-01 K16 Rollback Approval Gate

## Goal

- Add approval-request lifecycle for rollback operations.
- Enforce approval gate on rollback apply in production mode.

## Plan updates

- Updated `PLAN.md`:
  - recorded K16 started/completed
  - added next Sprint-K17 placeholders
- Updated `docs/v3_task_board.md`:
  - marked K16 tasks as `done`

## Changes

1. Rollback approval lifecycle APIs
   - File: `control_center/main.py`
   - Added:
     - `POST /metrics/workflows/alert-policy/rollback-approvals`
     - `POST /metrics/workflows/alert-policy/rollback-approvals/{approval_id}/approve`
     - `GET /metrics/workflows/alert-policy/rollback-approvals`

2. Rollback gate integration
   - File: `control_center/main.py`
   - Added env/config:
     - `WHERECODE_METRICS_ROLLBACK_REQUIRES_APPROVAL`
     - `WHERECODE_METRICS_ROLLBACK_APPROVER_ROLES`
     - `WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE`
   - Behavior:
     - when gate enabled and non-dry-run rollback, `approval_id` is required
     - approval must be approved and unused
     - approval reuse is rejected

3. Store enhancements
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Added:
     - rollback approval create/approve/consume/list methods
     - rollback apply now accepts `approval_id`
     - audit payload includes `rollback_approval_id`

4. API models and exports
   - Files:
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
     - `control_center/services/__init__.py`
   - Added:
     - rollback approval request/response models
     - rollback request `approval_id`
     - audit model fields for rollback request/approval ids

5. Script and docs
   - Script:
     - `scripts/v3_metrics_policy_rollback.sh`
     - supports `METRICS_POLICY_ROLLBACK_APPROVAL_ID`
   - Docs:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`

6. Tests and OpenAPI
   - Updated:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_openapi_contract.py`
   - Snapshot refreshed:
     - `tests/snapshots/openapi.snapshot.json`

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_metrics_policy_rollback_script.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - Result: `13 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `111 passed`

## Risk / follow-up

- Approval lifecycle currently has no expiration policy; next step (K17) adds TTL and cleanup.
