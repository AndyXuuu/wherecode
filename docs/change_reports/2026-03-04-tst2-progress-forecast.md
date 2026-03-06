# 2026-03-04 TST2 progress forecast

## Scope

- Add a TST2 progress/remaining report command to continuously track full-gate gap.

## Plan update

- `DOC-2026-03-04-TST2-PROGRESS-FORECAST` started (`doing`).
- `DOC-2026-03-04-TST2-PROGRESS-FORECAST` completed (`done`).

## Changes

- Added `/Users/andyxu/Documents/project/wherecode/scripts/tst2_progress_report.sh`.
  - Outputs JSON progress snapshot for `--profile full|local`.
  - Reuses `v3_milestone_gate.sh --milestone tst2-ready` output and computes:
    - `samples_remaining`
    - `coverage_remaining_seconds`
    - `coverage_progress_pct`
  - `--strict` exits non-zero when profile gate not passed.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`.
  - Added command: `tst2-progress [--profile full|local] [--strict]`.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Added `tst2_progress_report.sh` command usage and stationctl entry.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`.
  - Added `tst2-progress` examples.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`.
  - Added `tst2-progress` commands to immediate run list.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`.
  - Added `tst2-progress --profile full` in TST2 gate troubleshooting.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Added task completion and latest full/local progress snapshots.

## Validation

- `bash -n scripts/tst2_progress_report.sh scripts/stationctl.sh scripts/v3_milestone_gate.sh`
- `bash scripts/stationctl.sh tst2-progress --profile full`
  - `passed=false`
  - `samples_total=20`
  - `samples_remaining=268`
  - `coverage_remaining_seconds=83094`
- `bash scripts/stationctl.sh tst2-progress --profile local --strict`
  - `passed=true`
  - `next_phase=REL1`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
