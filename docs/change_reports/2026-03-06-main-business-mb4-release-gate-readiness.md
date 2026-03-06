# DOC-2026-03-06-MAIN-BUSINESS-MB4-RELEASE-GATE-READINESS

## Scope

- Run release baseline gate (`bash scripts/check_all.sh release`) and verify green result.
- Resolve two release-gate blockers in workflow API contract tests (execute aggregate metrics and confirmation detail assertion).
- Move MB4 sprint task status (`MB4-T1 done`, `MB4-T2 doing`, `MB4-T3 todo`).

## Changed Files

- `PLAN.md`
- `README.MD`
- `README.zh-CN.md`
- `control_center/main.py`
- `docs/release_map.md`
- `docs/v3_task_board.md`
- `tests/unit/test_v3_workflow_engine_api.py`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `bash scripts/check_all.sh release`
