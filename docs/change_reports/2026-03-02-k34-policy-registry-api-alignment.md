# 2026-03-02 K34 Verify Policy Registry API + Source Auth Alignment

## Goal

- Add control-center API for centralized verify policy registry management.
- Align policy-source URL consumption with protected API access via token header.

## Plan updates

- Updated `PLAN.md`:
  - added K34 sprint definition
  - marked K34 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K34-T1/T2/T3 as `done`

## Changes

1. Verify policy registry store + API
   - Files:
     - `control_center/services/metrics_alert_policy_store.py`
     - `control_center/main.py`
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
   - Added registry capabilities:
     - query current registry
     - update registry with role-guarded actor binding
     - list registry audits
     - export script-consumable source payload
   - Added endpoints:
     - `GET /metrics/workflows/alert-policy/verify-policy`
     - `PUT /metrics/workflows/alert-policy/verify-policy`
     - `GET /metrics/workflows/alert-policy/verify-policy/audits`
     - `GET /metrics/workflows/alert-policy/verify-policy/export`

2. Script source-auth adapter
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--policy-source-token <token>`
   - Behavior:
     - when `--policy-source-url` is HTTP(S), fetch request attaches `X-WhereCode-Token`
     - supports policy source from protected control-center endpoint

3. Tests
   - Files:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_metrics_rollback_approval_gc.py`
     - `tests/unit/test_openapi_contract.py`
   - Added coverage:
     - verify policy registry default read/update/audit/export flow
     - verify policy registry role guard and invalid resolver validation
     - script `--policy-source-token` option wiring with policy-source URL path
     - OpenAPI contract assertions for new paths/schemas

4. OpenAPI snapshot
   - File: `tests/snapshots/openapi.snapshot.json`
   - Updated snapshot for K34 API additions.

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - verify policy registry API usage
     - policy-source protected URL example with token
     - script option matrix update (`--policy-source-token`)

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `64 passed`
- Contract snapshot:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - Result: `22 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `165 passed`

## Risk / follow-up

- Script token option currently only sets `X-WhereCode-Token`; no custom header/auth scheme selection.
- Next step can add policy distribution retention/governance to avoid unbounded snapshot growth in distribution dir.
