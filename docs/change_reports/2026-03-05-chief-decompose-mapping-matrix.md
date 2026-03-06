# 2026-03-05 chief decompose mapping matrix

## Plan

- `DOC-2026-03-05-CHIEF-DECOMPOSE-MAPPING-MATRIX` started (`doing`)
- `DOC-2026-03-05-CHIEF-DECOMPOSE-MAPPING-MATRIX` completed (`done`)

## Changes

- Upgraded chief decomposition prompt contract for dev-project planning:
  - requires `metadata.decomposition.requirement_module_map`
  - requires full required-tag coverage in mapping
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added requirement-module matrix validation in `decompose-bootstrap`:
  - validate explicit mapping existence (configurable by `WHERECODE_DECOMPOSE_REQUIRE_EXPLICIT_MAP`)
  - validate mapping references only returned modules
  - validate every required coverage tag has mapped modules
  - persist mapping validation result in run metadata
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Refactored coverage keyword matching:
  - shared keyword map
  - per-module coverage inference helper
  - word-boundary matching to avoid substring false positives
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added tests:
  - success path with explicit requirement-module map
  - missing map rejection
  - unknown-module map rejection
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_v3_workflow_engine_api.py`
- Updated control-center env docs:
  - `/Users/andyxu/Documents/project/wherecode/control_center/README.md`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py -k "decompose_bootstrap"`
  - `6 passed`
- `control_center/.venv/bin/pytest -q tests/unit/test_openapi_contract.py`
  - `3 passed`
- `bash scripts/check_backend.sh`
  - `230 passed`
