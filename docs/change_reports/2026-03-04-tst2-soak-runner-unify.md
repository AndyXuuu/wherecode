# 2026-03-04 TST2 soak runner unify

## Scope

- Make TST2 soak runtime status resilient when pid files are missing but samples are still refreshing.
- Prevent duplicate soak writers against the same sample file.

## Plan update

- `DOC-2026-03-04-TST2-SOAK-RUNNER-UNIFY` started (`doing`).
- `DOC-2026-03-04-TST2-SOAK-RUNNER-UNIFY` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak.sh`.
  - Added per-samples-file lock (`*.lock`) to prevent concurrent writers.
  - Lock is acquired before run loop and auto-cleaned on exit.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_daemon.sh`.
  - Enhanced pid liveness check to treat `PermissionError` as process alive.
  - Added fresh-sample inference:
    - `status` reports `running (pid=unknown, source=fresh-samples)` when activity is fresh but pid file is unavailable.
    - `start` skips to avoid duplicate writers when fresh activity is detected.
    - `stop` returns non-zero if fresh activity exists but no manageable pid is available.
  - Kept compatibility for `.wherecode/run/tst2-soak.pid` and `.wherecode/run/tst2-soak-24h.pid`.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Documented lock behavior and fresh-sample inferred runner status.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Closed task and synced latest TST2 full snapshot.

## Validation

- `bash -n scripts/tst2_soak.sh scripts/tst2_soak_daemon.sh scripts/tst2_soak_status.sh scripts/v3_milestone_gate.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh soak status --strict`
  - `tst2 soak daemon: running (pid=unknown, source=fresh-samples)`
  - `guard_passed=true`
- `bash scripts/stationctl.sh soak start`
  - `tst2 soak appears active by fresh samples (pid file unavailable); skip new start to avoid duplicate writers`
- `bash scripts/stationctl.sh tst2-progress --profile full`
  - `samples_total=45`
  - `samples_remaining=243`
  - `coverage_remaining_seconds=81752`
  - `forecast_hours_remaining=22.75`
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`
  - non-zero as expected (still waiting full soak thresholds)
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
