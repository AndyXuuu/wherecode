# 2026-03-04 chief decompose bootstrap api

## Plan

- `DOC-2026-03-04-CHIEF-DECOMPOSE-BOOTSTRAP-API` started (`doing`)
- `DOC-2026-03-04-CHIEF-DECOMPOSE-BOOTSTRAP-API` completed (`done`)

## Changes

- Added workflow API request/response models:
  - `/Users/andyxu/Documents/project/wherecode/control_center/models/api.py`
  - `/Users/andyxu/Documents/project/wherecode/control_center/models/__init__.py`
- Added new endpoint for system-chief decomposition + bootstrap:
  - `POST /v3/workflows/runs/{run_id}/decompose-bootstrap`
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added decomposition prompt + module extraction helpers in control center:
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added tests for success and failure paths:
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_v3_workflow_engine_api.py`
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_openapi_contract.py`
- Updated OpenAPI snapshot:
  - `/Users/andyxu/Documents/project/wherecode/tests/snapshots/openapi.snapshot.json`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - `13 passed`
- `bash scripts/check_backend.sh`
  - `227 passed`
