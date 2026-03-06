# DOC-2026-03-06-MAIN-BUSINESS-MB2-T3-MIN-E2E-CONTRACTS

## Scope

- Add minimal e2e contract test for command-orchestrate flow covering latest telemetry and recovery execution API.
- Extend OpenAPI contract checks with orchestrate latest/recover paths and schema assertions.
- Move MB2 sprint status from `MB2-T3 doing` to `MB2-T3 done`, and set `MB2-T4 doing`.

## Changed Files

- `PLAN.md`
- `docs/v3_task_board.md`
- `tests/unit/test_protocol_contract.py`
- `tests/unit/test_openapi_contract.py`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `control_center/.venv/bin/python -m py_compile tests/unit/test_protocol_contract.py tests/unit/test_openapi_contract.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_protocol_contract.py -k "command_orchestrate"`
- `control_center/.venv/bin/pytest -q tests/unit/test_openapi_contract.py`
