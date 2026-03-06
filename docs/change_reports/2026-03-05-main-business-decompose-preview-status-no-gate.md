# DOC-2026-03-05-MAIN-BUSINESS-DECOMPOSE-PREVIEW-STATUS-NO-GATE

## Scope

- Remove preview-required confirmation gate (no blocking).
- Expose preview snapshot readiness/staleness on pending API.
- Keep preview cache audit fields for observability.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
