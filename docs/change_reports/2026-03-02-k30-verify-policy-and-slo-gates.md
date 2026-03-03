# 2026-03-02 K30 Verify Policy Controls + SLO Gates

## Goal

- Add multi-source verification policy controls.
- Add trend-based SLO gates for signer preflight and verify workflows.

## Plan updates

- Updated `PLAN.md`:
  - marked K30 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K30 tasks as `done`

## Changes

1. Verify source policy controls
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--verify-allowed-resolvers <csv>`
   - Behavior:
     - restricts resolver sources used in verification
     - supports: `manifest_output_path`, `manifest_file_uri`, `archive_basename_fallback`, `archive_relative_fallback`, `fetch_hook`
     - disallowed resolver source marks verification failed with explicit summary

2. Preflight SLO gates
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--preflight-slo-min-pass-rate <0..1>`
     - `--preflight-slo-max-consecutive-failures <n>`
   - Behavior:
     - evaluates `history_trend` from preflight history
     - outputs `policy_passed` and `slo_violations`
     - exits non-zero when SLO gate fails

3. Verify SLO gates
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--verify-slo-min-pass-rate <0..1>`
     - `--verify-slo-max-fetch-failures <n>`
   - Behavior:
     - evaluates trend summary pass rate + fetch failure count
     - outputs `policy_passed`, `slo_violations`, resolver/fetch diagnostics
     - exits non-zero when SLO gate fails

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - policy option mode guards
     - preflight SLO mode/history guard
     - preflight SLO gate violation path
     - resolver allowlist blocking archive fallback
     - verify fetch-failure SLO gate violation path

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - policy and SLO option usage examples
     - oncall commands with SLO gates enabled
     - option matrix updates for K30 controls

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `30 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `17 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `148 passed`

## Risk / follow-up

- Policy/SLO controls are CLI-driven and per-run; centralized policy profiles are not yet implemented.
- Next step: add reusable gate profiles (strict/standard/degraded) and preset loading.
