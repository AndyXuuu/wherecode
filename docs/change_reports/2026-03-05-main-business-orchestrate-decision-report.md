# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-DECISION-REPORT

## Scope

- Add dual-format decision report in orchestrate response.
- Provide `human_summary` for concise operator reading.
- Provide `machine` block for deterministic scheduler parsing.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
