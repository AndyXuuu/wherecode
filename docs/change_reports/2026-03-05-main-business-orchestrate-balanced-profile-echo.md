# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-BALANCED-PROFILE-ECHO

## Scope

- Add `balanced` strategy mode for orchestrate.
- Add strategy-aware execution profile echo to decision machine report.
- Apply balanced/safe execution tuning and strategy-aware recovery score adjustments.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
