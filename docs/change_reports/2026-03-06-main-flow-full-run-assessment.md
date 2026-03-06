# DOC-2026-03-06-MAIN-FLOW-FULL-RUN-ASSESSMENT

## Scope

- Execute one full main-flow replay (`command -> orchestrate -> recover -> execute`) on local stack.
- Run release + strict milestone gates and produce completion scoring assessment.

## Changed Files

- `PLAN.md`
- `docs/ops_reports/20260306T142701Z-main-flow-full-run.json`
- `docs/ops_reports/20260306T142701Z-recover.json`
- `docs/ops_reports/20260306T142701Z-execute.json`
- `docs/ops_reports/20260306T142701Z-run.json`
- `docs/ops_reports/20260306T142701Z-orchestrate-latest.json`
- `docs/ops_reports/20260306T142940Z-full-run-check-all-release.log`
- `docs/ops_reports/20260306T142940Z-full-run-milestone-gate.json`
- `docs/ops_reports/20260306T142940Z-main-flow-completion-assessment.md`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `bash scripts/stationctl.sh mb3-dry-run --requirements \"build stock sentiment pipeline with opinion crawl sentiment scoring and industry theme analysis\" --module-hints \"crawl,sentiment,theme,industry\" --requested-by go3-full-run`
- `curl -X POST /v3/workflows/runs/{run_id}/orchestrate/recover` (`action=reconfirm_decomposition`)
- `curl -X POST /v3/workflows/runs/{run_id}/execute`
- `bash scripts/check_all.sh release`
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`
