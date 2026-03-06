# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-ENTRYPOINT

## Scope

- Add single-call orchestration API to run decompose + execute in one entry.
- Reuse existing decompose and execute pipelines instead of duplicating workflow logic.
- Return orchestration status/reason plus before/after aggregate status snapshots.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
