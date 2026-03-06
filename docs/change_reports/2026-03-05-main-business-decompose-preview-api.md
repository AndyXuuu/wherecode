# DOC-2026-03-05-MAIN-BUSINESS-DECOMPOSE-PREVIEW-API

## Scope

- Add decompose bootstrap preview API for pre-execution orchestration visibility.
- Expose module/global task graph, dependencies, terminal tasks, and parallel groups.
- Keep preview source aligned with `pending_decomposition` / `chief_decomposition`.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/services/workflow_engine.py control_center/models/api.py control_center/models/__init__.py`
