# 2026-03-04 tst2 soak checkpoint automation

## Scope

- Add automatic TST2 soak checkpoint report generation and expose it via `stationctl`.

## Plan update

- `DOC-2026-03-04-TST2-SOAK-CHECKPOINT-AUTOMATION` started (`doing`).
- `DOC-2026-03-04-TST2-SOAK-CHECKPOINT-AUTOMATION` completed (`done`).

## Changes

- Added checkpoint generator script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_checkpoint.sh`
  - reads `tst2_soak_status.sh` JSON snapshot
  - reads daemon runtime state (`.wherecode/run/tst2-soak.pid`, `.wherecode/run/tst2-soak.start`)
  - writes markdown checkpoint to:
    - `docs/ops_reports/<timestamp>-tst2-live-checkpoint-auto.md`
  - supports:
    - `--strict` (guard must pass and daemon must be running)
    - `--output <path>`
- Added stationctl entry:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - `bash scripts/stationctl.sh soak-checkpoint [--strict] [--output <path>]`
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/tst2_soak_checkpoint.sh scripts/stationctl.sh scripts/tst2_soak_daemon.sh`
- `bash scripts/tst2_soak_checkpoint.sh`
- `bash scripts/stationctl.sh soak-checkpoint`
- `bash scripts/stationctl.sh --dry-run soak-checkpoint --strict`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - project backend tests: `1 passed`
