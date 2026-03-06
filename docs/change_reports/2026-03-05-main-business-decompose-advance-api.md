# DOC-2026-03-05-MAIN-BUSINESS-DECOMPOSE-ADVANCE-API

## Scope

- Add one-step decompose orchestration advance API for main-brain scheduling.
- Reuse aggregate `next_action` to execute preview/confirm/bootstrap/execute progression.
- Keep non-blocking behavior: return action status/reason instead of hard gate failures.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
