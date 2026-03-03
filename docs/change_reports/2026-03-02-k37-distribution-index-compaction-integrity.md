# 2026-03-02 K37 Distribution Index Compaction + Integrity Guard

## Goal

- Add automatic compaction for effective-policy distribution index.
- Add checksum-based integrity guard in distribution index query results.

## Plan updates

- Updated `PLAN.md`:
  - marked K37 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K37-T1/T2/T3 as `done`

## Changes

1. Index compaction
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Behavior:
     - distribution index (`distribution-index.jsonl`) now auto-compacts on write
     - keeps most recent entries under compaction limit
     - distribution output includes compaction metrics:
       - `effective_policy_distribution_index_compaction_max_entries`
       - `effective_policy_distribution_index_compaction_removed_total`
       - `effective_policy_distribution_index_total_after_compaction`

2. Integrity guard
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Behavior:
     - each distribution index entry stores `versioned_checksum_sha256`
     - list mode verifies checksum of referenced versioned file
     - list output includes:
       - `integrity_checked_total`
       - `integrity_failed_total`
       - `integrity_guard_passed`
       - per-entry `integrity_status` / `integrity_ok`
   - Added distribution output field:
     - `effective_policy_distribution_versioned_checksum_sha256`

3. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage:
     - list mode integrity success path
     - integrity mismatch detection after artifact tamper
     - index compaction behavior when seeded with oversized history
   - Updated existing tests to assert checksum/index-compaction fields.

4. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - integrity guard interpretation in list mode
     - compaction behavior notes
     - oncall action guidance for integrity guard failures

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `51 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `21 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `173 passed`

## Risk / follow-up

- Current compaction keeps latest entries by timestamp order only; no archival export of trimmed entries yet.
- Next step can add archival/restore drill for long-term index history handling.
