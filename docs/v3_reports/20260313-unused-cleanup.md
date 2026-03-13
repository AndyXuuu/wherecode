# V3-T16 Unused Cleanup Report

Date: 2026-03-13

## Scope

- Remove unused imports and unused local variables under `control_center`, `scripts`, `tests`.
- Keep runtime behavior unchanged.

## Commands

```bash
control_center/.venv/bin/ruff check control_center scripts tests --select F401,F841 --fix
control_center/.venv/bin/ruff check control_center scripts tests --select F401,F841
control_center/.venv/bin/vulture control_center/api control_center/executors control_center/models control_center/services scripts tests --min-confidence 100
bash scripts/check_backend.sh quick
control_center/.venv/bin/python -m pytest -q tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py
```

## Results

- `ruff`: 164 issues found, 164 resolved (`F401/F841` clear).
- `vulture` (`min-confidence=100` on project source dirs): no unused function/method candidates.
- `check_backend.sh quick`: 40 passed.
- OpenAPI tests: 4 passed.
- `check_all.sh main`: cannot run in current shell session because `127.0.0.1:8000` is not running.

## Follow-up Fixes

- Fixed model exports after import split:
  - `control_center/models/__init__.py`
- Fixed services re-export path for rollback exceptions:
  - `control_center/services/__init__.py`
