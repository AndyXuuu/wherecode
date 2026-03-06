# Ops Reports Index

Updated: 2026-03-06

## Stable Pointers

- `docs/ops_reports/latest_workflow_metrics.json`
- `docs/ops_reports/latest_tst2_t2_release_rehearsal.json`
- `docs/ops_reports/latest_mb3_dry_run_seed.json`

## Retained Milestone Evidence

- `docs/ops_reports/20260306T142940Z-main-flow-completion-assessment.md`
- `docs/ops_reports/20260306T143648Z-go3-target-host-validation-package.md`
- `docs/ops_reports/20260306T144823Z-go4-provider-remediation-report.md`
- `docs/ops_reports/20260306T152313Z-go4-closure-validation.md`
- `docs/ops_reports/20260306T152313Z-go4-provider-probe.json`

## Retention

- Keep `latest_*` pointers.
- Keep manual checkpoints (`YYYY-MM-DD-*.md`).
- Keep final milestone evidence files listed above.
- Remove disposable generated artifacts (`*.log`, `*.jsonl`, intermediate `*T*Z-*.json`).

## Quick Commands

- `ls -1 docs/ops_reports | sort`
- `rg -n "go4|go3|main-flow" docs/ops_reports`
