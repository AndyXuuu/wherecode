# 2026-03-02 K26 Signer Hook + Multi-format Verify Report

## Goal

- Add external signer hook support for manifest generation.
- Add multi-format verify report output (`txt` + `json`).

## Plan updates

- Updated `PLAN.md`:
  - marked K26 started/completed
  - added K27 backlog
- Updated `docs/v3_task_board.md`:
  - marked K26 tasks as `done`
  - set K27 as next action

## Changes

1. Signer hook integration
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--manifest-signer-cmd`
     - `--manifest-signer-timeout`
   - Hook protocol:
     - passes JSON payload to signer stdin
     - expects JSON output with `key_id` + `signature`
   - Behavior:
     - export with manifest can auto-fill signature fields from hook
     - hook timeout and failure paths are explicitly handled

2. Verify report format options
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--verify-report-format txt|json`
   - Behavior:
     - txt output keeps operator-readable summary
     - json output writes structured verify payload
   - Mode guards:
     - `--verify-report` requires `--verify-manifest`
     - invalid report format is rejected

3. Manifest schema extension in script flow
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - signer-provided key/signature fallback logic
     - execution metadata in verify output (`summary`, `signature_present`, `report_format`)

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - signer hook success path
     - verify report JSON format
     - invalid report-format guard
   - Existing manifest/verify/tamper tests remain passing

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - signer hook usage examples
     - txt/json verify report usage
     - oncall verification command updated to JSON report mode

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `31 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `132 passed`

## Risk / follow-up

- Signer hook is now pluggable, but preflight checks are not yet implemented.
- Next (K27): add signer preflight and verify trend summary output.
