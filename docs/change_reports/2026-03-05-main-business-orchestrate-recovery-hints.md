# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-RECOVERY-HINTS

## Scope

- Add automatic recovery action hints in orchestrate decision report.
- Expose `primary_recovery_action` and `recovery_actions` for scheduler retry routing.
- Include recovery actions in human summary for quick operator reading.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
