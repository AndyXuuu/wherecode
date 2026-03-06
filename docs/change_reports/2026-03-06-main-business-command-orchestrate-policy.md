# DOC-2026-03-06-MAIN-BUSINESS-COMMAND-ORCHESTRATE-POLICY

## Scope

- Implement command intent policy to route prefixed commands (default `/orchestrate`) into workflow orchestrate flow.
- Create workflow run from command context and execute orchestrate with parsed flags (strategy/module hints/max modules/execute).
- Persist orchestrate outcome into command/task metadata and return command success/failed by orchestration result.

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
- `control_center/.venv/bin/pytest -q tests/unit/test_protocol_contract.py -k "orchestrate_policy or auto_agent_routes_test_commands_to_test_agent"`
- `control_center/.venv/bin/pytest -q tests/unit/test_http_async_flow.py`
