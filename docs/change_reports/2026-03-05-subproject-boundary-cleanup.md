# DOC-2026-03-05-SUBPROJECT-BOUNDARY-CLEANUP

## Scope

- Remove subproject-specific coupling from main engineering codebase.
- Keep orchestration core and verification flow intact.
- Add explicit ownership boundary for `project/` workspace.

## Changed Files

- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/services/__init__.py`
- `control_center/.env.example`
- `control_center/README.md`
- `scripts/stationctl.sh`
- `scripts/check_backend.sh`
- `scripts/tst2_t2_release_rehearsal.sh`
- `scripts/README.md`
- `docs/runbook.md`
- `docs/release_map.md`
- `docs/troubleshooting.md`
- `docs/v3_task_board.md`
- `action_layer/README.md`
- `tests/unit/test_openapi_contract.py`
- `tests/unit/test_action_layer_llm_executor.py`
- `tests/unit/test_v3_workflow_engine_api.py`
- `tests/snapshots/openapi.snapshot.json`
- `README.MD`
- `PLAN.md`

## Validation

- `control_center/.venv/bin/python scripts/update_openapi_snapshot.py`
- `bash -n scripts/stationctl.sh`
- `bash scripts/check_backend.sh quick`
- `bash scripts/check_all.sh quick`
