# 2026-03-02 K38 Distribution Archive + Restore Drill

## Goal

- Persist compacted distribution-index entries into archive storage.
- Add restore drill mode to replay archived entries back to active index.

## Plan updates

- Updated `PLAN.md`:
  - marked K38 continued and completed
- Updated `docs/v3_task_board.md`:
  - marked K38-T1/T2/T3 as `done`

## Changes

1. Distribution archive persistence
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Behavior:
     - `distribution-index.jsonl` compaction now appends removed entries to `distribution-index-archive.jsonl`
     - archived entries include:
       - `archived_at`
       - `archive_reason=index_compaction`
     - verify/preflight distribution outputs now include:
       - `effective_policy_distribution_index_archive_path`
       - `effective_policy_distribution_index_archive_appended_total`

2. Restore drill mode
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added CLI:
     - `--restore-effective-policy-distributions`
     - `--restore-effective-policy-distributions-limit <count>`
     - `--restore-effective-policy-distributions-since-iso <iso>`
   - Behavior:
     - loads archive entries from `distribution-index-archive.jsonl`
     - filters by `since-iso`, applies `limit`, dedupes by `id` against current index
     - restores candidates into `distribution-index.jsonl`
     - returns drill stats:
       - `archive_scanned_total`
       - `restore_candidate_total`
       - `restored_total`
       - `skipped_existing_total`
       - `index_total_after_restore`

3. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage:
     - restore mode requires distribution dir
     - restore filters require restore mode
     - compaction archive append assertions
     - restore drill behavior (limit/since/dedupe)
   - Updated distribution snapshot assertions for archive output fields.

4. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - restore drill command examples
     - archive/index relationship notes
     - operator checks for new archive output fields

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `54 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `75 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `176 passed`

## Risk / follow-up

- Restore drill currently dedupes only by `id`; if IDs are reused incorrectly, stale payload can still be reinserted.
- Next step can add optional restore dry-run preview and strict checksum revalidation on restore path.
