# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-SUMMARY-UPGRADE

## Scope

- Add structured `decompose_payload` template support for orchestrate entry.
- Add standardized `decomposition_summary` output for orchestrate response.
- Reuse runtime decomposition metadata to expose module/task/coverage and confirmation-preview state.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
