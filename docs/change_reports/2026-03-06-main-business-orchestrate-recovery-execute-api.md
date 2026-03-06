# DOC-2026-03-06-MAIN-BUSINESS-ORCHESTRATE-RECOVERY-EXECUTE-API

## Scope

- Add runnable recovery API: `POST /v3/workflows/runs/{run_id}/orchestrate/recover`.
- Allow action source from request or latest decision primary recovery action.
- Connect recovery action to core flow handlers (`preview`, `confirm`, `advance-loop`, `execute`, `orchestrate`).

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`
- `tests/unit/test_v3_workflow_engine_api.py`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py control_center/services/workflow_engine.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py -k orchestrate_recover`
