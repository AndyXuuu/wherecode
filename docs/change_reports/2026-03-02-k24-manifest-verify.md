# 2026-03-02 K24 Manifest Index + Verify

## Goal

- Add export manifest index for purge-audit bundles.
- Add checksum verify command based on manifest entries.

## Plan updates

- Updated `PLAN.md`:
  - marked K24 started/completed
  - added K25 backlog
- Updated `docs/v3_task_board.md`:
  - marked K24 tasks as `done`
  - set K25 as next action

## Changes

1. Export manifest index
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--manifest <file>` in export mode
   - Behavior:
     - when export writes output file, manifest appends a jsonl record:
       - `id`
       - `created_at`
       - `output_path`
       - filters and checksum metadata

2. Verify command
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--verify-manifest`
     - `--manifest-id <id>` (optional)
     - `--verify-file <file>` (optional override)
   - Behavior:
     - verifies checksum from manifest against export file entries
     - returns JSON verification result
     - exits non-zero when verification fails

3. Mode/safety guards
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - verify mode cannot be combined with purge/export/rotate modes
     - `--verify-manifest` requires `--manifest`
     - export `--manifest` requires `--output`

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - export + manifest index write
     - verify-manifest success path
     - verify-manifest tamper detection failure

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - manifest export examples
     - verify-manifest command examples
     - oncall integrity check step

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `25 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `128 passed`

## Risk / follow-up

- Manifest currently stores checksum metadata without signature fields.
- Next (K25): add signed-manifest schema placeholder + verify summary report mode.
