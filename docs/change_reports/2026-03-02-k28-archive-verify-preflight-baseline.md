# 2026-03-02 K28 Archive Verify Adapter + Preflight Baseline Trend

## Goal

- Add archive fallback verification when manifest output path is moved.
- Add signer preflight history persistence and baseline trend summary.

## Plan updates

- Updated `PLAN.md`:
  - marked K28 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K28 tasks as `done`

## Changes

1. Archive verify adapter
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--verify-archive-dir <dir>`
   - Behavior:
     - verify resolves output from manifest path/file URI first
     - if missing, falls back to archive directory by basename/relative path
     - verify output includes `resolved_from` and optional `verify_archive_dir`

2. Signer preflight baseline trend
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--preflight-history <file>`
     - `--preflight-history-window <count>`
   - Behavior:
     - preflight can append JSONL records for each run
     - output includes `history_trend`:
       - `sample_size`
       - `passed_total`
       - `failed_total`
       - `pass_rate`
       - `consecutive_failures`

3. Mode guards and validation
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--verify-archive-dir` requires `--verify-manifest`
     - `--preflight-history`/`--preflight-history-window` require `--signer-preflight`
     - numeric parsing and lower bound normalization for preflight history window

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - archive-dir option guard
     - preflight-history option guard
     - preflight history trend over success+failure sequence
     - verify manifest archive fallback success path

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - archive fallback verify commands
     - preflight history baseline commands
     - updated option matrix for K28 features

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `22 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `17 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `140 passed`

## Risk / follow-up

- Archive fallback currently supports local filesystem paths and `file://` URIs only.
- Next step: add pluggable remote artifact resolvers (object storage / HTTP signed URL) for non-local archives.
