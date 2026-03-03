# 2026-03-01 K10 Metrics Alert + Ticket Draft

## Goal

- Add threshold-based alert evaluation on top of nightly metrics reporting.
- Generate incident ticket drafts automatically when thresholds are breached.

## Plan updates

- Updated `PLAN.md`:
  - added Sprint-K10 (`K10-T1/T2/T3`)
  - recorded started/completed entries
- Updated `docs/v3_task_board.md`:
  - added K10 tasks and marked all `done`

## Changes

1. Alert policy file
   - File: `control_center/metrics_alert_policy.json`
   - Includes thresholds for:
     - `failed_run_delta_gt`
     - `failed_run_count_gte`
     - `blocked_run_count_gte`
     - `waiting_approval_count_gte`
     - `in_flight_command_count_gte`

2. Alert check script
   - File: `scripts/v3_metrics_alert_check.sh`
   - Input:
     - metrics snapshot (`latest_workflow_metrics.json`)
     - policy JSON
     - output directory
   - Output:
     - when triggered, writes `*-metrics-alert-ticket.md`
   - Optional strict mode:
     - `METRICS_ALERT_EXIT_NONZERO=true`

3. Report snapshot enrichment
   - File: `scripts/v3_metrics_report.sh`
   - Added previous snapshot fields:
     - `previous_workflow_metrics`
     - `previous_summary_metrics`
   - Enables accurate delta-based checks.

4. Nightly workflow integration
   - File: `.github/workflows/nightly-metrics.yml`
   - Added alert-check step after nightly report generation.
   - Artifact now includes both metrics report and optional ticket draft.

5. Documentation updates
   - `docs/runbook.md`
   - `docs/oncall_checklist.md`
   - `scripts/README.md`

## Validation

- Script syntax:
  - `bash -n scripts/v3_metrics_report.sh scripts/v3_metrics_alert_check.sh scripts/ci_v3_rehearsal.sh scripts/v3_recovery_drill.sh scripts/v3_parallel_probe.sh`
- Script behavior checks:
  - threshold-hit sample generates ticket draft
  - no-hit sample returns clean pass
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `102 passed`

## Risk / follow-up

- Current alert policy is static JSON in repo; next iteration can add API-driven runtime policy management and audit history.
