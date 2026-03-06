# 2026-03-04 stationctl soak control

## Scope

- Route TST2 soak lifecycle through `stationctl` unified command entry.

## Plan update

- `DOC-2026-03-04-STATIONCTL-SOAK-CONTROL` started (`doing`).
- `DOC-2026-03-04-STATIONCTL-SOAK-CONTROL` completed (`done`).

## Changes

- Added `soak` command to stationctl:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - supports:
    - `bash scripts/stationctl.sh soak start`
    - `bash scripts/stationctl.sh soak status --strict`
    - `bash scripts/stationctl.sh soak stop`
    - `bash scripts/stationctl.sh soak restart`
  - forwards options to `scripts/tst2_soak_daemon.sh`
  - supports root `--dry-run` passthrough
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/stationctl.sh scripts/tst2_soak_daemon.sh`
- `bash scripts/stationctl.sh --dry-run soak start --duration 60 --interval 20`
- `bash scripts/stationctl.sh soak status`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - project backend tests: `1 passed`
