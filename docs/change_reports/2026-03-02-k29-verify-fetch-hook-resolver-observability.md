# 2026-03-02 K29 Verify Fetch Hook + Resolver Observability

## Goal

- Add pluggable fetch hook for verifying remote/moved artifacts.
- Improve verify observability with explicit resolver and fetch diagnostics.

## Plan updates

- Updated `PLAN.md`:
  - marked K29 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K29 tasks as `done`

## Changes

1. Verify fetch hook (pluggable resolver)
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--verify-fetch-cmd <cmd>`
     - `--verify-fetch-timeout <seconds>`
   - Behavior:
     - if manifest path / archive fallback not found, verify can call fetch hook
     - fetch hook protocol:
       - stdin JSON: `{"uri":"..."}`
       - stdout JSON: `{"local_path":"..."}`
     - fetched local file participates in normal checksum verification

2. Resolver observability
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added verify output fields:
     - `resolved_from` (`manifest_output_path` / `manifest_file_uri` / `archive_*` / `fetch_hook`)
     - `verify_fetch_cmd`
     - `fetch_error` (when fetch path resolution fails)
   - Text report now includes resolver/fetch diagnostics.

3. Guard rails and validation
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--verify-fetch-cmd` requires `--verify-manifest`
     - timeout parsing/normalization for `--verify-fetch-timeout`

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - `--verify-fetch-cmd` mode guard
     - verify manifest fallback via fetch hook for remote URI output path
     - resolver output assertions (`resolved_from=fetch_hook`)

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - fetch hook usage examples
     - oncall command including archive+fetch fallback
     - option matrix entries for fetch hook options

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `24 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `17 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `142 passed`

## Risk / follow-up

- Fetch hook is generic but currently shell-command driven; transport/auth are delegated externally.
- Next step: add policy controls for allowed URI schemes and hook exit-rate SLO alarms.
