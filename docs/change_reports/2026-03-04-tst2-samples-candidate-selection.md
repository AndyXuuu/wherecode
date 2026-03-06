# 2026-03-04 TST2 samples candidate selection

## Scope

- Fix default TST2 sample-file selection to avoid progress reset when a newer low-sample file exists.

## Plan update

- `DOC-2026-03-04-TST2-SAMPLES-CANDIDATE-SELECTION` started (`doing`).
- `DOC-2026-03-04-TST2-SAMPLES-CANDIDATE-SELECTION` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_status.sh`.
  - Replaced default file pick rule from “latest mtime” to:
    - highest non-empty sample count first
    - if tie, newer mtime
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/v3_milestone_gate.sh`.
  - Added shared soak row loader.
  - `tst2-ready` default sample file now follows same “highest progress first” selection.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_daemon.sh`.
  - `start` resume candidate now selects highest-progress unfinished file (tie by newer mtime), not latest file only.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Synced docs for status/daemon default sample selection behavior.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Recorded task closure and latest TST2 full/local snapshots.

## Validation

- `bash -n scripts/tst2_soak_status.sh scripts/tst2_soak_daemon.sh scripts/v3_milestone_gate.sh scripts/tst2_progress_report.sh`
- `bash scripts/stationctl.sh soak status --strict`
  - `samples_file=/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260304T130928Z-tst2-soak-samples.jsonl`
  - `samples_total=36`
  - `guard_passed=true`
- `bash scripts/stationctl.sh tst2-progress --profile full`
  - `samples_total=36`
  - `samples_remaining=252`
  - `coverage_remaining_seconds=82193`
  - `forecast_hours_remaining=22.83`
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`
  - non-zero as expected (`full` gate still waiting soak accumulation)
  - observed sample file fixed to `20260304T130928Z-tst2-soak-samples.jsonl`
- `bash scripts/stationctl.sh tst2-progress --profile local --strict`
  - `passed=true`
- `bash scripts/stationctl.sh soak-checkpoint --strict`
  - `full_profile_samples_remaining=252`
  - `full_profile_coverage_remaining_seconds=82193`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
