# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-TELEMETRY-LATEST-API

## Scope

- Persist latest orchestrate record into workflow run metadata.
- Add latest telemetry query endpoint: `GET /v3/workflows/runs/{run_id}/orchestrate/latest`.
- Return persisted strategy/status/actions/reason/decision/telemetry for orchestration observability.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
