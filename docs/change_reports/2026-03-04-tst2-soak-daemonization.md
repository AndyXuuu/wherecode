# 2026-03-04 tst2 soak daemonization

## Scope

- Add managed TST2 soak lifecycle commands for single-host long-run validation.
- Align release wording with single-host runtime context.

## Plan update

- `DOC-2026-03-04-TST2-SOAK-DAEMONIZATION` started (`doing`).
- `DOC-2026-03-04-TST2-SOAK-DAEMONIZATION` completed (`done`).

## Changes

- Added TST2 soak daemon manager:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_daemon.sh`
  - supports: `start|status|stop|restart`
  - supports runtime overrides:
    - `--duration`
    - `--interval`
    - `--probe-runs`
    - `--probe-workers`
    - `--probe-each-round`
    - `--skip-service-start`
    - `--fail-on-failed-delta`
    - `--max-failed-run-delta`
  - records runtime files:
    - `.wherecode/run/tst2-soak.pid`
    - `.wherecode/run/tst2-soak.log`
    - `.wherecode/run/tst2-soak.start`
  - hardens `start` path with post-start liveness verification (fail fast when process exits immediately)
- Updated script docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`
- Updated release docs for single-host terminology:
  - `/Users/andyxu/Documents/project/wherecode/README.md`
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/README.md`

## Checks

- `bash -n scripts/tst2_soak_daemon.sh scripts/tst2_soak.sh scripts/tst2_soak_status.sh`
- `bash scripts/tst2_soak_daemon.sh start --dry-run --duration 60 --interval 20 --probe-runs 1 --probe-workers 1 --probe-each-round false`
- `SOAK_DURATION_SECONDS=60 SOAK_INTERVAL_SECONDS=20 SOAK_PROBE_RUN_COUNT=1 SOAK_PROBE_WORKERS=1 SOAK_RUN_PROBE_EACH_ROUND=false bash scripts/tst2_soak.sh`
- `bash scripts/tst2_soak_daemon.sh status`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - project backend tests: `1 passed`
