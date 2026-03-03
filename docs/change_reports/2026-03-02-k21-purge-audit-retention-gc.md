# 2026-03-02 K21 Purge Audit Retention + GC

## Goal

- Add retention policy for purge-audit logs.
- Provide API + CLI cleanup flow for purge-audit logs with safety controls.

## Plan updates

- Updated `PLAN.md`:
  - marked K21 started/completed
  - added K22 backlog
- Updated `docs/v3_task_board.md`:
  - marked K21 tasks as `done`
  - set K22 as next action

## Changes

1. Store retention/cleanup logic
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Added:
     - `purge_rollback_approval_purge_audits(...)`
     - `keep_latest` + `older_than_seconds` retention controls
     - purge-audit event typing (`approval_purge`, `purge_audit_gc`)
     - full-file persist for purge-audit logs

2. API endpoints
   - File: `control_center/main.py`
   - Added:
     - `POST /metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge`
   - Updated:
     - safety check: reject when both `older_than_seconds` and `keep_latest` are unset
     - purge response now maps to dedicated purge-audit GC response model

3. API models
   - Files:
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
   - Added:
     - `PurgeRollbackApprovalPurgeAuditsRequest`
     - `PurgeRollbackApprovalPurgeAuditsResponse`
   - Updated:
     - `PurgeRollbackApprovalsAuditEntry` supports multi-event payloads (`event_type`, `keep_latest`)

4. Script enhancements
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--purge-audits` mode
     - `--keep-latest <count>`
     - safety check for purge-audits mode (requires `--older-than-seconds` or `--keep-latest`)
     - support purge-audit file env: `WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE`

5. Tests and OpenAPI
   - Files:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_metrics_rollback_approval_gc.py`
     - `tests/unit/test_openapi_contract.py`
     - `tests/snapshots/openapi.snapshot.json`
   - Added coverage for:
     - purge-audits GC endpoint success/safety/role-guard
     - script purge-audits mode + safety check
     - OpenAPI path/schema updates

6. Ops docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - purge-audits GC API examples
     - CLI usage for purge-audits mode
     - oncall guidance for purge-audit growth control

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - Result: `22 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `122 passed`

## Risk / follow-up

- Purge-audit export/archiving is still manual.
- Next (K22): add purge-audit export API and script mode for compliance archiving.
