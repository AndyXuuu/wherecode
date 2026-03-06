# DOC-2026-03-06-MAIN-BUSINESS-MB3-T4-RECOVERY-EXECUTE

## Scope

- Execute MB3 recovery action for latest blocked dry-run run via `/v3/workflows/runs/{run_id}/orchestrate/recover`.
- Persist recovery evidence (`action_status=executed`) for run `wfr_0120e72e0307`.
- Sync plan/task-board/readme sprint status from `MB3-T4 doing` to `MB3-T4 done`.

## Changed Files

- `PLAN.md`
- `README.MD`
- `README.zh-CN.md`
- `docs/v3_task_board.md`
- `docs/ops_reports/20260306T132756Z-mb3-t4-recover-execute.json`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `bash scripts/stationctl.sh mb3-dry-run --requirements "build stock sentiment pipeline with opinion crawl sentiment scoring and industry theme analysis" --module-hints "crawl,sentiment,theme,industry" --requested-by mb3-seed`
- `curl -X POST http://127.0.0.1:8000/v3/workflows/runs/wfr_0120e72e0307/orchestrate/recover -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" -H "Content-Type: application/json" -d '{"action":"retry_with_decompose_payload","strategy":"balanced","requirements":"build stock sentiment pipeline with opinion crawl sentiment scoring and industry theme analysis","module_hints":["crawl","sentiment","theme","industry"],"max_modules":6,"requested_by":"mb3-recover","execute":false,"confirmed_by":"owner"}'`
