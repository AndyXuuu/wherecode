# 2026-03-04 TST2 progress ETA

## Scope

- Add ETA forecast fields to TST2 progress output for predictable full-gate tracking.

## Plan update

- `DOC-2026-03-04-TST2-PROGRESS-ETA` started (`doing`).
- `DOC-2026-03-04-TST2-PROGRESS-ETA` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/v3_milestone_gate.sh`.
  - `tst2-ready` required payload now includes:
    - `tst2_duration_seconds`
    - `tst2_interval_seconds`
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_progress_report.sh`.
  - Added forecast fields:
    - `forecast_rounds_remaining`
    - `forecast_seconds_remaining`
    - `forecast_hours_remaining`
    - `projected_ready_at_utc`
  - Forecast based on max of:
    - sample-count remaining
    - coverage-seconds remaining
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Documented ETA fields of `tst2-progress`.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`.
  - Added ETA field check hint for TST2 gate troubleshooting.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Added task completion and latest ETA snapshots.

## Validation

- `bash -n scripts/tst2_progress_report.sh scripts/v3_milestone_gate.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh tst2-progress --profile full`
  - `samples_total=25`
  - `samples_remaining=263`
  - `coverage_remaining_seconds=82794`
  - `forecast_hours_remaining=23.0`
  - `projected_ready_at_utc=2026-03-05T13:04:36Z`
- `bash scripts/stationctl.sh tst2-progress --profile local --strict`
  - `passed=true`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
