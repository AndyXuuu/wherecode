# 2026-03-03 K45-T1/T2/T3 State File Merge Hardening

## Scope
- Add merge-safe state-file writer.
- Keep existing JSON keys when list/restore writes state snapshots.
- Add tests and docs.

## Changed files
- `scripts/v3_metrics_rollback_approval_gc.sh`
- `tests/unit/test_metrics_rollback_approval_gc.py`
- `docs/runbook.md`
- `docs/oncall_checklist.md`
- `scripts/README.md`
- `PLAN.md`
- `docs/v3_task_board.md`
- `.wherecode/state.json`

## Checks
- `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
- `control_center/.venv/bin/pytest -q`
