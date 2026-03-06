# 2026-03-05 chief decompose human confirm gate

## Plan

- `DOC-2026-03-05-CHIEF-DECOMPOSE-HUMAN-CONFIRM-GATE` started (`doing`)
- `DOC-2026-03-05-CHIEF-DECOMPOSE-HUMAN-CONFIRM-GATE` completed (`done`)

## Changes

- Added human confirmation gate for decomposition stage:
  - `decompose-bootstrap` now produces pending plan and waits for confirmation
  - new confirm endpoint: `POST /v3/workflows/runs/{run_id}/decompose-bootstrap/confirm`
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added execute guard:
  - `POST /v3/workflows/runs/{run_id}/execute` returns `409` when decomposition confirmation is pending
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added configuration:
  - `WHERECODE_DECOMPOSE_REQUIRE_CONFIRMATION` (default `true`)
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
  - `/Users/andyxu/Documents/project/wherecode/control_center/.env.example`
  - `/Users/andyxu/Documents/project/wherecode/control_center/README.md`
- Extended decomposition/confirmation models:
  - response now includes confirmation fields
  - added confirm request/response contracts
  - `/Users/andyxu/Documents/project/wherecode/control_center/models/api.py`
  - `/Users/andyxu/Documents/project/wherecode/control_center/models/__init__.py`
- Added/updated tests:
  - decompose success path now requires explicit confirm before bootstrap
  - execute-before-confirm blocked
  - confirm reject path
  - confirm token mismatch path
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_v3_workflow_engine_api.py`
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_openapi_contract.py`
- Updated OpenAPI snapshot:
  - `/Users/andyxu/Documents/project/wherecode/tests/snapshots/openapi.snapshot.json`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py -k "decompose_bootstrap" tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - `10 passed`
- `bash scripts/check_backend.sh`
  - `234 passed`
