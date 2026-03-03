# 2026-03-01 K14 Rollback API Driven Flow

## Goal

- Move metrics policy rollback into authenticated API flow.
- Make rollback script default to API-mediated execution.

## Plan updates

- Updated `PLAN.md`:
  - recorded K14 started/completed entries
- Updated `docs/v3_task_board.md`:
  - marked `K14-T1/T2/T3` as `done`

## Changes

1. Rollback API endpoint
   - File: `control_center/main.py`
   - Added:
     - `POST /metrics/workflows/alert-policy/rollback`
   - Behavior:
     - supports `dry_run`
     - uses existing role guard and identity binding (`updated_by` == authenticated role when auth enabled)
     - returns rollback result payload

2. Rollback data models
   - File: `control_center/models/api.py`
   - Added:
     - `RollbackMetricsAlertPolicyRequest`
     - `RollbackMetricsAlertPolicyResponse`
   - Extended:
     - `MetricsAlertPolicyAuditEntry` now includes optional `rollback_from_audit_id`

3. Policy store rollback capability
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Added:
     - `rollback_to_audit(...)`
     - `get_audit(...)`
   - Supports dry-run preview and applied rollback with appended audit entry.

4. API-driven rollback script
   - File: `scripts/v3_metrics_policy_rollback.sh`
   - Default mode now calls rollback API with:
     - token header
     - role header
     - rollback request payload
   - Retained fallback maintenance mode:
     - `--local-file-mode`

5. Tests and OpenAPI
   - Updated:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_metrics_policy_rollback_script.py`
     - `tests/unit/test_openapi_contract.py`
   - Snapshot refreshed:
     - `tests/snapshots/openapi.snapshot.json`

6. Ops docs
   - Updated:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_metrics_policy_rollback_script.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `109 passed`

## Risk / follow-up

- Fallback `--local-file-mode` bypasses API guard; keep for emergency/offline maintenance only and prefer default API mode in production operations.
