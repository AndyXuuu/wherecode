# 2026-03-02 K35 Effective Policy Distribution Retention + Governance

## Goal

- Add retention governance to effective-policy distribution outputs.
- Expose cleanup observability fields for operational verification.

## Plan updates

- Updated `PLAN.md`:
  - added K35 sprint definition
  - marked K35 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K35-T1/T2/T3 as `done`

## Changes

1. Distribution retention policy
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--distribute-effective-policy-retain-seconds <seconds>`
     - `--distribute-effective-policy-keep-latest <count>`
   - Behavior:
     - supports cleanup of historical version files under distribution dir
     - `latest.json` is always refreshed
     - current run version file is protected from same-run cleanup
     - mode guard enforces retention flags require distribution dir mode

2. Distribution observability fields
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added result fields:
     - `effective_policy_distribution_cleanup_enabled`
     - `effective_policy_distribution_retain_seconds`
     - `effective_policy_distribution_keep_latest`
     - `effective_policy_distribution_removed_total`
     - `effective_policy_distribution_remaining_versioned_total`
     - `effective_policy_distribution_removed_paths`

3. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage:
     - retain-seconds flag requires distribution dir
     - keep-latest flag requires distribution dir
     - retention cleanup removes stale version files and reports cleanup stats
   - Updated existing distribution test to assert new governance fields.

4. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - distribution retention command examples
     - option matrix updates for retention governance flags
     - oncall command updated with keep-latest + retain-seconds guidance

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `46 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `21 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `168 passed`

## Risk / follow-up

- Distribution cleanup currently runs inline with verify/preflight flow; large directories can add latency.
- Next step can add distribution index and query API for fleet-level visibility.
