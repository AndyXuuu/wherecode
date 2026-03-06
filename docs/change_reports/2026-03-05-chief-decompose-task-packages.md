# 2026-03-05 chief decompose task packages

## Plan

- `DOC-2026-03-05-CHIEF-DECOMPOSE-TASK-PACKAGES` started (`doing`)
- `DOC-2026-03-05-CHIEF-DECOMPOSE-TASK-PACKAGES` completed (`done`)

## Changes

- Extended chief decomposition prompt contract:
  - requires `metadata.decomposition.module_task_packages`
  - each module package must include tasks with `role` + `objective`
  - each module must cover `module-dev/doc-manager/qa-test/security-review`
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added module task package extraction/inference/validation:
  - explicit package extraction from metadata
  - fallback default package inference (used only when strict mode disabled)
  - strict validation gates in `decompose-bootstrap`
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added runtime strict-mode env switch:
  - `WHERECODE_DECOMPOSE_REQUIRE_TASK_PACKAGE` (default `true`)
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Updated decompose metadata persistence:
  - stores package validation outputs:
    - `module_task_packages`
    - `missing_task_package_modules`
    - `invalid_task_package_roles`
    - `missing_task_package_roles`
    - `task_package_explicit`
  - `/Users/andyxu/Documents/project/wherecode/control_center/main.py`
- Added tests:
  - success path includes valid task packages
  - missing task packages rejected
  - missing required task roles rejected
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_v3_workflow_engine_api.py`
- Updated env docs:
  - `/Users/andyxu/Documents/project/wherecode/control_center/README.md`
  - `/Users/andyxu/Documents/project/wherecode/control_center/.env.example`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py -k "decompose_bootstrap"`
  - `8 passed`
- `control_center/.venv/bin/pytest -q tests/unit/test_openapi_contract.py`
  - `3 passed`
- `bash scripts/check_backend.sh`
  - `232 passed`
