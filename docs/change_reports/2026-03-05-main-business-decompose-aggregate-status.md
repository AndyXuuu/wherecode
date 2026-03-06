# DOC-2026-03-05-MAIN-BUSINESS-DECOMPOSE-AGGREGATE-STATUS

## Scope

- Add decompose aggregate status API for single-call orchestration state view.
- Aggregate pending confirmation, preview snapshot, and workitem readiness metrics.
- Provide `next_action` hint for main-brain scheduler decisions.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
