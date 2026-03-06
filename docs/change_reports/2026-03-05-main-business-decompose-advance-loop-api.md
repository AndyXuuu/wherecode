# DOC-2026-03-05-MAIN-BUSINESS-DECOMPOSE-ADVANCE-LOOP-API

## Scope

- Add decompose advance-loop API for multi-step auto progression in one call.
- Reuse single-step advance logic and aggregate status to stop at stable milestones.
- Return step trace and action status summary for main-brain scheduling feedback.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
