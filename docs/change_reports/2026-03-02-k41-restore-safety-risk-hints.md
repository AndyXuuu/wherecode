# 2026-03-02 K41 Restore Safety Risk + Operator Hints

## Goal

- Provide explicit safety risk grading for restore drill output.
- Provide actionable operator hints to reduce unsafe restore execution.

## Plan updates

- Updated `PLAN.md`:
  - marked K41 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K41-T1/T2/T3 as `done`

## Changes

1. Restore safety risk grading
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added restore output field:
     - `restore_safety_risk_level` with values `low|medium|high`
   - Risk rules:
     - `high`: non-dry-run restore writes without integrity check
     - `medium`: integrity failures exist and fail-gate is disabled
     - `low`: dry-run or guarded restore paths

2. Operator recommendations and summary
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added restore output fields:
     - `restore_recommendations`
     - `summary`
   - Hint examples:
     - enable integrity verification before write
     - enable fail-on-integrity gate for CI
     - remove `--dry-run` after review
     - adjust since/limit filters when no entries restored

3. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Updated restore tests to assert:
     - risk level output for dry-run/non-dry-run/integrity-fail paths
     - recommendation hints for risky modes
     - summary text in restore responses

4. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - explanation of restore risk/hint fields
     - oncall requirement to review risk/hints before non-dry-run restore

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `59 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `80 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `181 passed`

## Risk / follow-up

- Current hints are rule-based strings; they do not include environment-specific remediation.
- Next step can add optional path remap suggestions when cross-host archive paths are detected.
