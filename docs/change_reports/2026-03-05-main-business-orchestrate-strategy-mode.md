# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-STRATEGY-MODE

## Scope

- Add `strategy=speed|safe` to orchestrate request/response and machine report.
- Apply safe-mode execution tuning (smaller loop budget + refresh preview) in orchestrate.
- Apply strategy-aware recovery scoring adjustments for decision report ranking.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
