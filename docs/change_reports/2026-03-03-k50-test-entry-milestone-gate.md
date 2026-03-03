# 2026-03-03 K50-T1/T2/T3 Test-Entry Milestone Gate

## Scope
- Add milestone gate script for test-entry.
- Add strict gate checks and persisted milestone snapshot.
- Move board/state to TST1 after milestone pass.

## Changed files
- `scripts/v3_milestone_gate.sh`
- `tests/unit/test_v3_milestone_gate_script.py`
- `PLAN.md`
- `docs/v3_task_board.md`
- `.wherecode/state.json`
- `.wherecode/milestones.json`
- `docs/runbook.md`
- `docs/oncall_checklist.md`
- `scripts/README.md`

## Checks
- `bash -n scripts/v3_milestone_gate.sh`
- `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- `control_center/.venv/bin/pytest -q tests/unit/test_v3_milestone_gate_script.py tests/unit/test_metrics_rollback_approval_gc.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_v3_milestone_gate_script.py tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
- `control_center/.venv/bin/pytest -q`
