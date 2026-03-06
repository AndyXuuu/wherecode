# DOC-2026-03-05-MAIN-BUSINESS-DECOMPOSE-PREVIEW-CACHE

## Scope

- Add cached preview snapshot persistence for decompose bootstrap graph.
- Add `refresh` query switch to force preview re-computation.
- Keep cache consistency by decomposition fingerprint matching.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
