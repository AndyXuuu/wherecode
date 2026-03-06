# DOC-2026-03-05-MAIN-BUSINESS-EXECUTE-ENTRY-AUTO-ADVANCE

## Scope

- Integrate decompose advance-loop into main execute entry for unified scheduler trigger.
- Extend execute request/response with auto-advance controls and trace payload.
- Preserve confirmation safety: execute still returns 409 when pending confirmation remains.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
