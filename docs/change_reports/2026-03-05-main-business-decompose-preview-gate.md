# DOC-2026-03-05-MAIN-BUSINESS-DECOMPOSE-PREVIEW-GATE

## Scope

- Add optional preview gate before decompose confirmation.
- Return preview cache audit fields for cache hit visibility.
- Reset stale preview cache when new decomposition payload is generated.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
