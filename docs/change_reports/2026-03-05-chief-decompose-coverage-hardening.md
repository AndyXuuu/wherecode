# 2026-03-05 chief decompose coverage hardening

## Plan

- `DOC-2026-03-05-CHIEF-DECOMPOSE-COVERAGE-HARDENING` started (`doing`)
- `DOC-2026-03-05-CHIEF-DECOMPOSE-COVERAGE-HARDENING` completed (`done`)

## Changes

- Strengthened chief decomposition prompt for development-project module planning:
  - explicitly states software development project context
  - requires requirement points, module responsibilities, and coverage check payload
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added decomposition coverage validation:
  - derive required coverage tags from requirements + module hints
  - infer coverage from module keys and declared metadata tags
  - fail bootstrap when required tags are missing
  - persist coverage validation result in run metadata
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added and updated tests:
  - prompt contains project decomposition declaration
  - missing required coverage tags returns 422
  - metadata records required/missing coverage tags
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_v3_workflow_engine_api.py`
- Fixed keyword matching precision:
  - avoid false-positive substring matches (e.g. `daily` vs `ai`)
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py -k "decompose_bootstrap" tests/unit/test_openapi_contract.py`
  - `4 passed`
- `bash scripts/check_backend.sh`
  - `228 passed`
