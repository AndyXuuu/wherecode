# 2026-03-02 K27 Signer Preflight + Verify Trend Summary

## Goal

- Add signer-hook preflight checks before export signing.
- Add trend summary in verify output/report for oncall decisions.

## Plan updates

- Updated `PLAN.md`:
  - marked K27 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K27 tasks as `done`

## Changes

1. Signer preflight mode
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--signer-preflight`
     - `--manifest-signer-cmd`
     - `--manifest-signer-timeout`
   - Behavior:
     - runs signer hook with synthetic payload
     - outputs structured JSON (`success`, `summary`, `key_id`, `signature_preview`)
     - timeout/failure returns non-zero with error summary in JSON

2. Verify trend summary
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--verify-trend-window <count>`
   - Behavior:
     - verify response now includes `trend_summary`
     - trend scans recent manifest entries and computes:
       - `sample_size`
       - `passed_total`
       - `failed_total`
       - `pass_rate`
       - `failed_manifest_entry_ids`
     - txt/json reports include trend data

3. Mode guards and validation
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--signer-preflight` cannot combine with purge/export/rotate/verify
     - `--signer-preflight` requires `--manifest-signer-cmd`
     - `--verify-trend-window` requires `--verify-manifest`
     - numeric parsing and bounds for trend window

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - signer preflight success/failure/timeout
     - verify trend option guard
     - verify JSON report trend payload

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - signer preflight command examples
     - verify trend-window usage
     - oncall checklist step for signer preflight + trend verify

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `35 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `136 passed`

## Risk / follow-up

- Trend summary currently verifies files directly from manifest output paths; remote artifact verification is not included.
- Next step: add remote/object-store verification adapter if archive moves off local disk.
