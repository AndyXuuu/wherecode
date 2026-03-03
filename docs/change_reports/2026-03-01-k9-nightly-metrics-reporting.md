# 2026-03-01 K9 Nightly Metrics Reporting

## Goal

- Add nightly workflow-metrics reporting as part of M6 hardening.
- Provide script + scheduled workflow + operations documentation.

## Plan updates

- Updated `PLAN.md`:
  - added Sprint-K9 (`K9-T1/T2/T3`)
  - recorded started/completed entries
- Updated `docs/v3_task_board.md`:
  - added K9 tasks and marked all as `done`

## Changes

1. Nightly report script
   - File: `scripts/v3_metrics_report.sh`
   - Capabilities:
     - collects `/metrics/workflows` and `/metrics/summary`
     - writes markdown report `*-workflow-metrics.md`
     - maintains baseline snapshot `latest_workflow_metrics.json`
     - calculates delta vs previous snapshot
     - optional guard: fail when failed-run delta increases (`METRICS_FAIL_ON_FAILED_DELTA=true`)

2. Scheduled GitHub workflow
   - File: `.github/workflows/nightly-metrics.yml`
   - Trigger:
     - nightly cron (`0 17 * * *`)
     - manual `workflow_dispatch`
   - Output:
     - uploads `nightly-workflow-metrics` artifact

3. Documentation updates
   - `docs/runbook.md`: added command and environment variables for nightly metrics reporting.
   - `docs/oncall_checklist.md`: added daily snapshot generation check.
   - `scripts/README.md`: added `v3_metrics_report.sh`.
   - `docs/README.md`: indexed `docs/ops_reports/`.
   - `docs/ops_reports/README.md`: documented ops report output files.

## Validation

- Script syntax:
  - `bash -n scripts/v3_metrics_report.sh scripts/ci_v3_rehearsal.sh scripts/v3_recovery_drill.sh scripts/v3_parallel_probe.sh`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `102 passed`

## Risk / follow-up

- In restricted local sandboxes, runtime health checks may fail if localhost port binding is blocked.
- Nightly workflow should be validated in GitHub Actions runner environment where service processes can bind ports normally.
