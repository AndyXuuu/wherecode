# 2026-03-03 K46-T1/T2/T3 List Risk Hardening

## Scope
- Add list-mode risk-level, recommendations, and summary output.
- Add list fail-gate context and state snapshot fields.
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
