# 2026-03-04 TST2 ready watchdog

## Scope

- Add a watchdog command to continuously poll TST2 readiness and checkpoint output.

## Plan update

- `DOC-2026-03-04-TST2-READY-WATCHDOG` started (`doing`).
- `DOC-2026-03-04-TST2-READY-WATCHDOG` completed (`done`).

## Changes

- Added `/Users/andyxu/Documents/project/wherecode/scripts/tst2_ready_watchdog.sh`.
  - Polls `tst2-progress --profile <full|local>` by round.
  - Optional per-round `soak-checkpoint --strict`.
  - Emits markdown report under `docs/ops_reports/`.
  - Supports `--interval` / `--max-rounds` / `--strict`.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`.
  - Added command: `tst2-watch`.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Added `tst2-watch` to stationctl command list.
  - Added watchdog usage and strict behavior note.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Closed task state and synced latest full profile snapshot.

## Validation

- `bash -n scripts/tst2_ready_watchdog.sh scripts/stationctl.sh scripts/tst2_progress_report.sh scripts/tst2_soak_checkpoint.sh`
- `bash scripts/stationctl.sh tst2-watch --profile full --interval 1 --max-rounds 1`
  - `watchdog_report=/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260304T142835Z-tst2-ready-watchdog.md`
  - `watchdog_passed=false` (expected, full gate not yet reached)
- `bash scripts/stationctl.sh tst2-progress --profile full`
  - `samples_total=53`
  - `samples_remaining=235`
  - `coverage_remaining_seconds=81356`
  - `forecast_hours_remaining=22.67`
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`
  - non-zero as expected (pending full soak thresholds)
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
