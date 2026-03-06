# DOC-2026-03-06-MAIN-BUSINESS-MB3-T5-UNBLOCK-FLOW

## Scope

- Add synthetic decomposition fallback for chief non-success responses to unblock command-orchestrate main flow.
- Complete MB3 end-to-end loop evidence (`dry-run -> recover -> execute`) for stock-sentiment scenario.
- Mark MB3 milestone as done and move active sprint to MB4.

## Changed Files

- `PLAN.md`
- `README.MD`
- `README.zh-CN.md`
- `control_center/main.py`
- `control_center/.env.example`
- `control_center/README.md`
- `docs/release_map.md`
- `docs/runbook.md`
- `docs/v3_task_board.md`
- `tests/unit/test_v3_workflow_engine_api.py`
- `docs/ops_reports/20260306T134242Z-mb3-dry-run-seed.json`
- `docs/ops_reports/20260306T134242Z-mb3-t5-full-loop.json`
- `docs/ops_reports/latest_mb3_dry_run_seed.json`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py tests/unit/test_v3_workflow_engine_api.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py -k "execute_failure_path or decompose_bootstrap_success or synthetic_fallback or non_success_status"`
- `bash scripts/stationctl.sh mb3-dry-run --requirements "build stock sentiment pipeline with opinion crawl sentiment scoring and industry theme analysis" --module-hints "crawl,sentiment,theme,industry" --requested-by mb3-seed`
- `curl -X POST http://127.0.0.1:8000/v3/workflows/runs/wfr_ba22687d5d8b/orchestrate/recover -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" -H "Content-Type: application/json" -d '{"action":"reconfirm_decomposition","confirmed_by":"owner"}'`
- `curl -X POST http://127.0.0.1:8000/v3/workflows/runs/wfr_ba22687d5d8b/execute -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" -H "Content-Type: application/json" -d '{"max_loops":20,"auto_advance_decompose":true,"auto_advance_max_steps":8}'`
