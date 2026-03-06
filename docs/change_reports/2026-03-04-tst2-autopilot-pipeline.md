# 2026-03-04 TST2 autopilot pipeline

## Scope

- Add one command to orchestrate TST2 flow: soak ensure, readiness watch, and optional strict T2 rehearsal.

## Plan update

- `DOC-2026-03-04-TST2-AUTOPILOT-PIPELINE` started (`doing`).
- `DOC-2026-03-04-TST2-AUTOPILOT-PIPELINE` completed (`done`).

## Changes

- Added `/Users/andyxu/Documents/project/wherecode/scripts/tst2_autopilot.sh`.
  - Step 1: ensure soak writer (`stationctl soak start`).
  - Step 2: run readiness watch (`stationctl tst2-watch`).
  - Step 3: when ready and not skipped, trigger `stationctl tst2-rehearsal --strict`.
  - Supports `--profile` / `--watch-interval` / `--watch-max-rounds` / `--checkpoint-each-round` / `--skip-rehearsal` / `--strict` / `--dry-run`.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`.
  - Added command: `tst2-autopilot`.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Added `tst2-autopilot` in command index and usage notes.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`.
  - Added `tst2-watch` and `tst2-autopilot` examples.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`.
  - Added immediate run list entries for `tst2-watch` and `tst2-autopilot`.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Closed task and synced latest full profile progress snapshot.

## Validation

- `bash -n scripts/tst2_autopilot.sh scripts/tst2_ready_watchdog.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh tst2-autopilot --profile full --watch-interval 1 --watch-max-rounds 1 --skip-rehearsal`
  - `autopilot_ready=false` (expected, full gate not reached)
  - `autopilot_report=/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260304T143211Z-tst2-ready-watchdog.md`
- `bash scripts/stationctl.sh tst2-progress --profile full`
  - `samples_total=57`
  - `samples_remaining=231`
  - `coverage_remaining_seconds=81151`
  - `forecast_hours_remaining=22.58`
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`
  - non-zero as expected (pending full soak thresholds)
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
