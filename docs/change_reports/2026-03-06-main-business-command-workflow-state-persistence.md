# DOC-2026-03-06-MAIN-BUSINESS-COMMAND-WORKFLOW-STATE-PERSISTENCE

## Scope

- Persist `workflow_state_latest` snapshot for command-driven orchestrate execution.
- Sync latest workflow state and recovery hint into command/task/run metadata.
- Extend command orchestrate contract tests to verify workflow-state persistence fields.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/README.md`
- `docs/v3_task_board.md`
- `tests/unit/test_protocol_contract.py`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py tests/unit/test_protocol_contract.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_protocol_contract.py -k "command_orchestrate_policy"`
- `control_center/.venv/bin/pytest -q tests/unit/test_http_async_flow.py`
