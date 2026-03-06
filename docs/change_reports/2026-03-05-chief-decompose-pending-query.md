# 2026-03-05 chief decompose pending query

## Plan

- `DOC-2026-03-05-CHIEF-DECOMPOSE-PENDING-QUERY` started (`doing`)
- `DOC-2026-03-05-CHIEF-DECOMPOSE-PENDING-QUERY` completed (`done`)

## Changes

- Added pending query API:
  - `GET /v3/workflows/runs/{run_id}/decompose-bootstrap/pending`
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added pending query response model:
  - `DecomposeBootstrapPendingWorkflowResponse`
  - `/Users/andyxu/Documents/project/wherecode/control_center/models/api.py`
  - `/Users/andyxu/Documents/project/wherecode/control_center/models/__init__.py`
- Added lifecycle tests:
  - pending exists after decompose
  - pending cleared after approve
  - rejected record still queryable
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_v3_workflow_engine_api.py`
- Updated OpenAPI contract/snapshot:
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_openapi_contract.py`
  - `/Users/andyxu/Documents/project/wherecode/tests/snapshots/openapi.snapshot.json`
- Updated API README:
  - `/Users/andyxu/Documents/project/wherecode/control_center/README.md`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py tests/unit/test_openapi_contract.py`
  - `21 passed`
- `control_center/.venv/bin/pytest -q tests/unit/test_openapi_snapshot.py tests/unit/test_openapi_contract.py`
  - `4 passed`
- `bash scripts/check_backend.sh`
  - `236 passed`
