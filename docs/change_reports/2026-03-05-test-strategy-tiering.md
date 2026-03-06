# 2026-03-05 test strategy tiering

## Plan

- `DOC-2026-03-05-TEST-STRATEGY-TIERING` started (`doing`)
- `DOC-2026-03-05-TEST-STRATEGY-TIERING` completed (`done`)

## Changes

- Replanned backend checks into two scopes:
  - `bash scripts/check_backend.sh quick` (default, core workflow set)
  - `bash scripts/check_backend.sh full` (full backend pytest)
  - `/Users/andyxu/Documents/project/wherecode/scripts/check_backend.sh`
- Replanned aggregate checks with tiered scopes:
  - default `quick`
  - `release` now runs backend full + frontend + project checks
  - added `backend-quick` and `backend-full`
  - `/Users/andyxu/Documents/project/wherecode/scripts/check_all.sh`
- Updated station command entry:
  - `bash scripts/stationctl.sh check quick|dev|release`
  - default is `quick`
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
- Updated active docs and plan to follow tiered strategy:
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/README.MD`
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/check_backend.sh scripts/check_all.sh scripts/stationctl.sh`
- `bash scripts/check_backend.sh quick`
  - `39 passed`
- `bash scripts/check_all.sh quick`
  - `39 passed`
- `bash scripts/check_backend.sh full`
  - `236 passed`
- `bash scripts/check_all.sh release`
  - backend `236 passed`
  - command_center build passed
  - project checks passed
- `bash scripts/stationctl.sh check quick`
  - `39 passed`
