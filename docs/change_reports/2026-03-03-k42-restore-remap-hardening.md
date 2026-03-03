# 2026-03-03 K42-T1/T2/T3 Restore Remap Hardening

## Scope
- Add restore path remap inputs and mode guards.
- Add remap-aware integrity/restore pipeline.
- Add tests and docs for remap flow.

## Changed files
- `scripts/v3_metrics_rollback_approval_gc.sh`
- `tests/unit/test_metrics_rollback_approval_gc.py`
- `docs/runbook.md`
- `docs/oncall_checklist.md`
- `scripts/README.md`
- `.wherecode/state.json`
- `PLAN.md`
- `docs/v3_task_board.md`

## Checks
- `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
- `control_center/.venv/bin/pytest -q`
