# 2026-03-01 K15 Rollback Idempotency + Conflict Guard

## Goal

- Prevent duplicate rollback writes when retrying rollback requests.
- Add clear conflict protection for invalid rollback attempts.

## Plan updates

- Updated `PLAN.md`:
  - recorded K15 started/completed entries
- Updated `docs/v3_task_board.md`:
  - marked `K15-T1/T2/T3` as `done`

## Changes

1. Rollback idempotency support
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Added `idempotency_key` handling in `rollback_to_audit(...)`:
     - same `idempotency_key` + same target audit -> replay response without new audit write
     - replay response includes `idempotent_replay=true`

2. Conflict guards
   - File: `control_center/services/metrics_alert_policy_store.py`
   - Added `PolicyRollbackConflictError` for:
     - idempotency key reused with different rollback target
     - rollback target policy already matches current policy (no-op apply)
   - File: `control_center/main.py`
   - Maps rollback conflicts to `409` responses.

3. API model updates
   - File: `control_center/models/api.py`
   - Added fields:
     - request: `idempotency_key`
     - response: `idempotent_replay`
     - audit entry: `rollback_request_id`

4. API-driven script enhancement
   - File: `scripts/v3_metrics_policy_rollback.sh`
   - Added env:
     - `METRICS_POLICY_ROLLBACK_IDEMPOTENCY_KEY`
   - Payload now includes `idempotency_key` when provided.

5. Tests and contracts
   - Updated:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_openapi_contract.py`
   - Updated snapshot:
     - `tests/snapshots/openapi.snapshot.json`
   - Existing rollback script tests kept valid in `--local-file-mode`.

6. Documentation
   - Updated:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added usage guidance and conflict behavior notes.

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_metrics_policy_rollback_script.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `110 passed`

## Risk / follow-up

- Current idempotency scope is based on rollback audit history in local storage.
- Next step can add explicit rollback approval gate for production mode and richer operator audit context.
