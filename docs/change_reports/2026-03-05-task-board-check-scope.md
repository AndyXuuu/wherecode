# 2026-03-05 task board check scope

## Plan

- `DOC-2026-03-05-TASK-BOARD-CHECK-SCOPE` started (`doing`)
- `DOC-2026-03-05-TASK-BOARD-CHECK-SCOPE` completed (`done`)

## Changes

- Added explicit validation scope definition section in task board:
  - `quick/full/release`
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
- Added `Check Scope` column to active sprint tasks and release track stages:
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
- Split board actions into:
  - `Validation Cadence`
  - `Next Action`
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
- Updated plan task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `rg -n "Validation Scope|Check Scope|Validation Cadence|check_all.sh quick|check_backend.sh full|milestone tst2-ready" docs/v3_task_board.md docs/runbook.md docs/release_map.md PLAN.md`
- `bash scripts/check_all.sh quick`
  - `39 passed`
