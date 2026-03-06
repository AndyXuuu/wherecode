# DOC-2026-03-05-CHANGE-REPORT-BASELINE-CONSOLIDATION

## Scope

- Consolidate `docs/change_reports/` entry docs into compact operational index.
- Add a phase map for fast navigation by milestone batch.
- Normalize legacy terminology in historical report content.

## Changed Files

- `PLAN.md`
- `docs/README.md`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`
- `docs/change_reports/2026-03-03-independent-project-root-setup.md`
- `docs/change_reports/2026-03-04-readme-phase-sync-automation.md`
- `docs/change_reports/2026-03-04-stationctl-soak-control.md`
- `docs/change_reports/2026-03-04-tst2-autopilot-pipeline.md`
- `docs/change_reports/2026-03-04-tst2-checkpoint-eta-sync.md`
- `docs/change_reports/2026-03-04-tst2-milestone-gate.md`
- `docs/change_reports/2026-03-04-tst2-milestone-profile.md`
- `docs/change_reports/2026-03-04-tst2-progress-eta.md`
- `docs/change_reports/2026-03-04-tst2-progress-forecast.md`
- `docs/change_reports/2026-03-04-tst2-ready-watchdog.md`
- `docs/change_reports/2026-03-04-tst2-samples-candidate-selection.md`
- `docs/change_reports/2026-03-04-tst2-soak-checkpoint-automation.md`
- `docs/change_reports/2026-03-04-tst2-soak-checkpoint-strict-gate-fix.md`
- `docs/change_reports/2026-03-04-tst2-soak-daemonization.md`
- `docs/change_reports/2026-03-04-tst2-soak-detach-hardening.md`
- `docs/change_reports/2026-03-04-tst2-soak-resume-continuity.md`
- `docs/change_reports/2026-03-04-tst2-soak-runner-unify.md`
- `docs/change_reports/2026-03-04-tst2-t2-latest-report.md`
- `docs/change_reports/2026-03-04-tst2-t2-rehearsal-automation.md`
- `docs/change_reports/2026-03-05-release-scope-triggers.md`
- `docs/change_reports/2026-03-05-subproject-boundary-cleanup.md`
- `docs/change_reports/2026-03-05-task-board-check-scope.md`
- `docs/change_reports/2026-03-05-history-doc-boundary-cleanup.md`

## Validation

- `rg -n "<legacy-subproject-keywords>" docs/change_reports docs/ops_reports` (no matches)
- `rg -n "Change Reports 说明|建议模板|风险与后续事项" docs/change_reports/README.md docs/change_reports/MAP.md docs/README.md` (no matches)
