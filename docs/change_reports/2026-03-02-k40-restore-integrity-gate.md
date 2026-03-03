# 2026-03-02 K40 Restore Integrity Verification + Gate

## Goal

- Harden restore drill with integrity checks on archive candidates.
- Add fail-fast gate for CI/operator workflows when restore integrity fails.

## Plan updates

- Updated `PLAN.md`:
  - marked K40 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K40-T1/T2/T3 as `done`

## Changes

1. Restore integrity verification
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added CLI:
     - `--restore-effective-policy-verify-integrity`
   - Behavior:
     - restore candidates are validated by:
       - `versioned_checksum_sha256` presence
       - `versioned_path` presence
       - versioned file existence
       - sha256 checksum match
     - integrity-failed candidates are skipped from restore writes
   - Added restore output fields:
     - `restore_integrity_check_enabled`
     - `integrity_checked_total`
     - `integrity_failed_total`
     - `integrity_failed_ids`
     - `integrity_guard_passed`
     - `restore_skipped_integrity_total`

2. Restore fail gate
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added CLI:
     - `--restore-effective-policy-fail-on-integrity-error`
   - Guard rules:
     - requires restore mode
     - requires `--restore-effective-policy-verify-integrity`
   - Behavior:
     - when enabled and `integrity_guard_passed=false`, restore exits non-zero
     - output includes `restore_integrity_fail_on_error`

3. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage:
     - verify-integrity option requires restore mode
     - fail-on-integrity requires verify-integrity
     - integrity verify path skips invalid candidates and restores only valid ones
     - fail-on-integrity mode exits non-zero
   - Updated restore tests for new output fields.

4. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - integrity verify and fail-gate restore commands
     - field interpretation for restore integrity outputs
     - oncall guidance: dry-run -> verify-integrity -> optional fail-gate restore

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `59 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `80 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `181 passed`

## Risk / follow-up

- Integrity verification currently depends on local file visibility from archived `versioned_path`.
- Next step can add optional path remap strategy (archive root remap) for cross-host drill portability.
