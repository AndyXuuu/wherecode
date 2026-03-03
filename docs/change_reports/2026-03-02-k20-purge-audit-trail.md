# 2026-03-02 K20 Purge Audit Trail

## Goal

- Add audit trail for rollback-approval purge actions.
- Expose purge-audit query API for ops/compliance.

## Plan updates

- Updated `PLAN.md`:
  - marked K20 started and completed
  - added K21 backlog
- Updated `docs/v3_task_board.md`:
  - marked K20 tasks as `done`
  - set K21 as next action

## Changes

1. Purge audit persistence in policy store
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Added:
     - purge audit file path support
     - purge action logging (`requested_by`, parameters, result, timestamp)
     - `purge_audit_id` return field
     - purge audit list method

2. Purge API + query API
   - File: `control_center/main.py`
   - Updated:
     - `POST /metrics/workflows/alert-policy/rollback-approvals/purge`
       - now records actor in audit trail
       - returns `purge_audit_id`
   - Added:
     - `GET /metrics/workflows/alert-policy/rollback-approvals/purge-audits`

3. API models
   - Files:
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
   - Added:
     - `PurgeRollbackApprovalsAuditEntry`
   - Updated:
     - purge request/response models include retention/audit fields

4. GC script integration
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - default actor `METRICS_ROLLBACK_APPROVAL_GC_REQUESTED_BY` (default `ops-script`)
     - purge request now writes audit entries

5. Tests and OpenAPI
   - Files:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_metrics_rollback_approval_gc.py`
     - `tests/unit/test_openapi_contract.py`
     - `tests/snapshots/openapi.snapshot.json`
   - Added coverage for:
     - purge audit id in purge responses
     - purge audit query endpoint behavior
     - CLI purge audit output
     - new OpenAPI schemas/path

6. Ops docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - purge-audits query usage
     - new env vars for purge/audit operations
     - oncall checklist step for cleanup audit verification

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - Result: `18 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `118 passed`

## Risk / follow-up

- Purge audits now accumulate indefinitely.
- Next (K21): add purge-audit retention + cleanup controls.
