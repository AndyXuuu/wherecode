# 2026-03-02 K25 Signed-Manifest Schema + Verify Report

## Goal

- Extend manifest records with signature-related metadata fields.
- Add operator-friendly verify report output mode.

## Plan updates

- Updated `PLAN.md`:
  - marked K25 started/completed
  - added K26 backlog
- Updated `docs/v3_task_board.md`:
  - marked K25 tasks as `done`
  - set K26 as next action

## Changes

1. Manifest signature schema extension
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added export options:
     - `--manifest-key-id`
     - `--manifest-signature`
   - Behavior:
     - when export writes manifest, entry now includes:
       - `key_id`
       - `signature`

2. Verify report mode
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added verify option:
     - `--verify-report <file>`
   - Behavior:
     - writes human-readable summary report (status, checksums, key metadata)
     - verify JSON output includes:
       - `summary`
       - `key_id`
       - `signature_present`
       - `report_path` (when report file is requested)

3. Validation guards
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--verify-report` requires `--verify-manifest`
     - `--manifest-key-id/--manifest-signature` require `--manifest` in export mode
     - verify mode remains exclusive from purge/export/rotate modes

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - manifest key/signature field persistence
     - verify report file generation
     - tamper failure summary
     - invalid `--verify-report` mode guard

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - signed-manifest export example
     - verify-report usage
     - oncall integrity check with report output

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `27 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `129 passed`

## Risk / follow-up

- Manifest signature is currently a schema placeholder (no real signer integration).
- Next (K26): add external signer hook and multi-format verify report output.
