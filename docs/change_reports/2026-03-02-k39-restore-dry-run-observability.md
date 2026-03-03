# 2026-03-02 K39 Restore Dry-Run + Observability

## Goal

- Add non-mutating restore drill preview flow.
- Improve restore drill output for operator diagnosis.

## Plan updates

- Updated `PLAN.md`:
  - marked K39 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K39-T1/T2/T3 as `done`

## Changes

1. Restore dry-run preview
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Behavior:
     - restore drill now respects global `--dry-run`
     - in dry-run mode:
       - archive candidates are evaluated
       - active index is not mutated
       - output includes `would_restore_total` for planned writes

2. Restore candidate observability fields
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added restore output fields:
     - `dry_run`
     - `restore_candidate_ids`
     - `would_restore_total`
     - `would_restore_ids`
     - `restored_ids`
     - `skipped_existing_ids`
   - Existing counters remain:
     - `restore_candidate_total`
     - `restored_total`
     - `skipped_existing_total`
     - `index_total_after_restore`

3. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage:
     - restore output id summaries on non-dry-run path
     - dry-run restore does not mutate `distribution-index.jsonl`
   - Updated assertions for new restore observability keys.

4. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - restore dry-run example command
     - field interpretation for `would_restore_*` and id summary outputs
     - oncall sequence: dry-run first, then real restore

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `55 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `76 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `177 passed`

## Risk / follow-up

- Restore still trusts archive entry payload content; integrity revalidation is currently handled by list mode, not restore mode.
- Next sprint can add optional restore integrity guard (checksum/file existence policy).
