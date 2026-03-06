# 2026-03-05 validation cadence sync

## Plan

- `DOC-2026-03-05-VALIDATION-CADENCE-SYNC` started (`doing`)
- `DOC-2026-03-05-VALIDATION-CADENCE-SYNC` completed (`done`)

## Changes

- Synced task board to explicit cadence commands:
  - daily loop uses `quick`
  - gate phase uses `full/release`
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
- Synced release map objective with cadence rule:
  - `quick` for daily loop, `full/release` for gates
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
- Synced runbook with cadence rule heading and command set:
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
- Synced plan task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `rg -n "check_all.sh quick|check_backend.sh full|stationctl.sh check quick|milestone_gate" docs/v3_task_board.md docs/runbook.md docs/release_map.md PLAN.md scripts/README.md`
- `bash scripts/check_all.sh quick`
  - `39 passed`
