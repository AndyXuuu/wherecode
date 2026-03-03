# 2026-03-02 K22 Purge Audit Export

## Goal

- Add purge-audit export endpoint for compliance archiving.
- Add CLI export mode with time-window filters and optional file output.

## Plan updates

- Updated `PLAN.md`:
  - marked K22 started/completed
  - added K23 backlog
- Updated `docs/v3_task_board.md`:
  - marked K22 tasks as `done`
  - set K23 as next action

## Changes

1. Export API endpoint
   - File: `control_center/main.py`
   - Added:
     - `GET /metrics/workflows/alert-policy/rollback-approvals/purge-audits/export`
   - Supports query filters:
     - `event_type`
     - `created_after`
     - `created_before`
     - `limit` (bounded)

2. Export response models
   - Files:
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
   - Added:
     - `ExportRollbackApprovalPurgeAuditsResponse`
   - Updated:
     - purge audit entry schema supports multi-event payload fields

3. Store filtering support
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Updated:
     - purge-audit list method now supports event type and created_at range filtering

4. CLI export mode
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--export-purge-audits`
     - `--from-iso`
     - `--to-iso`
     - `--event-type`
     - `--limit`
     - `--output`
   - Behavior:
     - exports JSON payload to stdout or target file
     - keeps purge modes mutually exclusive with export mode

5. Tests and OpenAPI
   - Files:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_metrics_rollback_approval_gc.py`
     - `tests/unit/test_openapi_contract.py`
     - `tests/snapshots/openapi.snapshot.json`
   - Added coverage for:
     - export endpoint filtering by type/time
     - CLI export output file generation
     - OpenAPI path/schema contract updates

6. Ops docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - export API usage examples
     - CLI export command examples
     - oncall export archiving step

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - Result: `24 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `124 passed`

## Risk / follow-up

- Exported files currently rely on external retention management.
- Next (K23): add export integrity metadata and rotation policy.
