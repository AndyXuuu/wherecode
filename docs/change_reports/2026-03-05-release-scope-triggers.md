# 2026-03-05 release scope triggers

## Plan

- `DOC-2026-03-05-RELEASE-SCOPE-TRIGGERS` started (`doing`)
- `DOC-2026-03-05-RELEASE-SCOPE-TRIGGERS` completed (`done`)

## Changes

- Added explicit `Trigger` column for release-scope execution in task board:
  - active sprint tasks (`TST2-T2/TST2-T3`)
  - pre-dev task rows in historical board snapshot
  - release track stages
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
- Added `Entry Trigger` column to release map stage table:
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
- Updated plan task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `rg -n "Trigger|Entry Trigger|check_all.sh quick|check_all.sh release|milestone test-entry|milestone tst2-ready" docs/v3_task_board.md docs/release_map.md docs/runbook.md PLAN.md`
- `bash scripts/check_all.sh quick`
  - `39 passed`
