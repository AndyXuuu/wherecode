# 2026-03-04 stationctl check scope

## Scope

- Make `stationctl check` support optional scope selection.
- Default to lightweight single-machine check path.

## Plan update

- `DOC-2026-03-04-STATIONCTL-CHECK-SCOPE` started (`doing`).
- `DOC-2026-03-04-STATIONCTL-CHECK-SCOPE` completed (`done`).

## Changes

- Updated stationctl command contract:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - `check [dev|release]`
  - default scope: `dev`
  - `release` triggers heavy gate path
  - invalid scope now returns clear error (`allowed: dev|release`)
- Added dedicated check dispatcher:
  - `run_check` routes to `scripts/check_all.sh <scope>`
  - keeps `--dry-run` behavior
- Updated command examples and docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh` (usage/examples)
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/README.md`
- Synced task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/stationctl.sh scripts/check_all.sh`
- `bash scripts/stationctl.sh help`
- `bash scripts/stationctl.sh --dry-run check`
- `bash scripts/stationctl.sh --dry-run check release`
