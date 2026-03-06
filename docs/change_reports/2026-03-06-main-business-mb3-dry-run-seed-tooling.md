# DOC-2026-03-06-MAIN-BUSINESS-MB3-DRY-RUN-SEED-TOOLING

## Scope

- Add MB3 dry-run seed script to create `project/task`, submit `/orchestrate` command, poll terminal status, and write ops evidence JSON.
- Add `stationctl` command entry `mb3-dry-run` to call the MB3 seed script from unified command gateway.
- Allow dry-run evidence to pass when command is non-success but `workflow_run_id` exists, and expose `primary_recovery_action` for next-step recovery.
- Run one real MB3 dry-run and persist evidence output (`workflow_run_id=wfr_9fe6f9c1acac`, `primary_recovery_action=retry_with_decompose_payload`).
- Sync MB3 sprint status and operation docs across plan, runbook, script index, release map, task board, and bilingual README.

## Changed Files

- `PLAN.md`
- `README.MD`
- `README.zh-CN.md`
- `scripts/mb3_dry_run_seed.sh`
- `scripts/stationctl.sh`
- `scripts/README.md`
- `docs/runbook.md`
- `docs/release_map.md`
- `docs/v3_task_board.md`
- `docs/ops_reports/20260306T132330Z-mb3-dry-run-seed.json`
- `docs/ops_reports/latest_mb3_dry_run_seed.json`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `bash -n scripts/mb3_dry_run_seed.sh scripts/stationctl.sh`
- `bash scripts/mb3_dry_run_seed.sh --dry-run`
- `bash scripts/stationctl.sh mb3-dry-run --dry-run`
- `bash scripts/stationctl.sh mb3-dry-run --requirements "build stock sentiment pipeline with opinion crawl sentiment scoring and industry theme analysis" --module-hints "crawl,sentiment,theme,industry" --requested-by mb3-seed`
