# 2026-03-02 K36 Distribution Index Persistence + Query Mode

## Goal

- Add durable index records for each effective-policy distribution event.
- Add query mode to inspect distribution history with operational filters.

## Plan updates

- Updated `PLAN.md`:
  - marked K36 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K36-T1/T2/T3 as `done`

## Changes

1. Distribution index persistence
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Behavior:
     - each distribution now appends an entry to `distribution-index.jsonl`
     - index entry includes:
       - id/created_at/mode
       - versioned/latest paths
       - policy profile/source
       - cleanup config and cleanup result counters
   - Distribution output now includes:
     - `effective_policy_distribution_index_path`
     - `effective_policy_distribution_index_entry_id`

2. Distribution query mode
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--list-effective-policy-distributions`
     - `--list-effective-policy-distributions-limit <count>`
     - `--list-effective-policy-distributions-mode verify_manifest|signer_preflight`
     - `--list-effective-policy-distributions-since-iso <iso>`
   - Behavior:
     - list mode requires `--distribute-effective-policy-dir`
     - filter options require list mode
     - list mode is isolated from verify/preflight/purge/export/rotate modes
     - output includes scanned/matched totals and filtered entry list

3. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage:
     - list mode requires distribution dir
     - list filters require list mode
     - distribution writes index file + index entry fields
     - list mode returns filtered distribution history
   - Updated distribution retention test to assert index-path presence.

4. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - list mode command examples
     - option matrix updates for distribution index query options
     - oncall baseline query for distribution index

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `49 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `21 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `171 passed`

## Risk / follow-up

- Index file grows append-only; no compaction policy yet.
- Next step can add index compaction + checksum integrity guard for long-term operations.
