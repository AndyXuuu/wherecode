# 2026-03-02 K17-K19 Rollback Approval Ops Hardening

## Goal

- Close K17 approval TTL + cleanup baseline.
- Deliver K18 approval ops APIs (stats + online purge).
- Deliver K19 retention window (`older_than_seconds`) for safer cleanup.

## Plan updates

- Updated `PLAN.md`:
  - marked K17 complete
  - marked K18 complete
  - added and completed K19
  - added K20 backlog
- Updated `docs/v3_task_board.md`:
  - marked K17/K18/K19 as `done`
  - added K20 as next sprint

## Changes

1. Approval lifecycle hardening (K17 baseline)
   - Files:
     - `control_center/services/metrics_alert_policy_store.py`
     - `control_center/models/api.py`
     - `control_center/main.py`
     - `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - approval TTL with `expires_at`
     - `expired` status handling in approve/consume
     - cleanup command for used/expired approvals

2. Approval ops APIs (K18)
   - Files:
     - `control_center/main.py`
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
     - `control_center/services/metrics_alert_policy_store.py`
   - Added endpoints:
     - `GET /metrics/workflows/alert-policy/rollback-approvals/stats`
     - `POST /metrics/workflows/alert-policy/rollback-approvals/purge`
   - Added models:
     - `RollbackApprovalStatsResponse`
     - `PurgeRollbackApprovalsRequest`
     - `PurgeRollbackApprovalsResponse`

3. Retention window for purge (K19)
   - Files:
     - `control_center/services/metrics_alert_policy_store.py`
     - `control_center/main.py`
     - `control_center/models/api.py`
     - `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `older_than_seconds` in purge API and store logic
     - CLI support: `--older-than-seconds <seconds>`
     - retention check based on approval `updated_at/created_at`

4. Tests and OpenAPI
   - Files:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_metrics_rollback_approval_gc.py`
     - `tests/unit/test_openapi_contract.py`
     - `tests/snapshots/openapi.snapshot.json`
   - Added coverage for:
     - expired approval rejection
     - stats and purge endpoints
     - purge retention window behavior
     - OpenAPI schema/paths for new APIs and fields

5. Ops docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - stats endpoint usage
     - purge API notes
     - retention-window cleanup commands

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - Result: `18 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `118 passed`

## Risk / follow-up

- Purge operations are currently observable via response payloads only.
- Next (K20): persist purge audit trail and provide query API for compliance/postmortem.
