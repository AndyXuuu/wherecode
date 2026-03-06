# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-RECOVERY-SCORING

## Scope

- Add priority/confidence scoring for orchestrate recovery actions.
- Expose scored action list in machine report for deterministic action selection.
- Include primary scored recovery hint in human summary text.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
