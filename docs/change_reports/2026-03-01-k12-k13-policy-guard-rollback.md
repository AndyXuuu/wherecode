# 2026-03-01 K12-K13 Policy Guard + Rollback

## Goal

- K12: enforce role-based permission and identity binding on metrics policy updates.
- K13: add rollback tooling for policy changes with dry-run safety mode.

## Plan updates

- Updated `PLAN.md`:
  - added Sprint-K12 and Sprint-K13
  - marked K12 and K13 completed
- Updated `docs/v3_task_board.md`:
  - added K12/K13 tasks and marked all `done`

## Changes

1. Policy update role guard
   - File: `control_center/main.py`
   - Added:
     - `WHERECODE_METRICS_ALERT_POLICY_UPDATE_ROLES` parsing
     - `X-WhereCode-Role` extraction and authorization checks
   - Rules:
     - auth enabled: role header required for policy update
     - role must be in configured whitelist
     - `updated_by` must match authenticated role

2. Runtime policy API coverage
   - Files:
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
     - `control_center/services/__init__.py`
   - Added policy/audit API schemas and exports.

3. Policy store hardening
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Improved normalization for non-numeric string values.

4. Rollback tooling (K13)
   - New script: `scripts/v3_metrics_policy_rollback.sh`
   - Supports:
     - rollback by `audit_id`
     - `--dry-run` preview mode
     - append rollback audit entry after apply

5. Tests
   - Updated: `tests/unit/test_v3_metrics_alert_policy_api.py`
     - covers missing role / forbidden role / identity mismatch / success
   - New: `tests/unit/test_metrics_policy_rollback_script.py`
     - covers dry-run no-write and apply rollback paths
   - Updated: `tests/conftest.py` for isolated policy store per test

6. Ops docs
   - Updated:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added policy update role requirements and rollback command examples.

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_policy_rollback_script.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `107 passed`

## Risk / follow-up

- Rollback currently edits files locally; next iteration can expose rollback as authenticated API endpoint for centralized audit and access control.
