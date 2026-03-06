# 2026-03-04 TST2 checkpoint ETA sync

## Scope

- Keep `soak-checkpoint` and `tst2-progress` ETA/remaining fields aligned for full-gate tracking.

## Plan update

- `DOC-2026-03-04-TST2-CHECKPOINT-ETA-SYNC` started (`doing`).
- `DOC-2026-03-04-TST2-CHECKPOINT-ETA-SYNC` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_checkpoint.sh`.
  - Added `Full gate forecast` section in markdown output.
  - Synced stdout fields with progress report:
    - `full_profile_samples_remaining`
    - `full_profile_coverage_remaining_seconds`
    - `full_profile_forecast_hours_remaining`
    - `full_profile_projected_ready_at_utc`
  - Used Bash-compatible line reads for metric extraction.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Added checkpoint forecast output fields in script docs.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Closed task state and wrote latest full/local progress snapshots.

## Validation

- `bash -n scripts/tst2_soak_checkpoint.sh scripts/tst2_progress_report.sh scripts/stationctl.sh scripts/v3_milestone_gate.sh`
- `bash scripts/stationctl.sh soak-checkpoint --strict`
  - `guard_passed=true`
  - `full_profile_samples_remaining=258`
  - `full_profile_coverage_remaining_seconds=82493`
  - `full_profile_forecast_hours_remaining=22.92`
  - `full_profile_projected_ready_at_utc=2026-03-05T13:04:37Z`
- `bash scripts/stationctl.sh tst2-progress --profile full`
  - `samples_total=30`
  - `samples_remaining=258`
  - `coverage_remaining_seconds=82493`
  - `forecast_hours_remaining=22.92`
- `bash scripts/stationctl.sh tst2-progress --profile local --strict`
  - `passed=true`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
