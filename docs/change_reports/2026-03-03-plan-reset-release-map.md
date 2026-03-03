# 2026-03-03 plan reset + release map

## Scope

- Clear completed backlog from PLAN.
- Keep only active sprint and release path.
- Add dedicated release map doc.

## Plan update

- `DOC-2026-03-03-PLAN-RESET-RELEASE-MAP` started (`doing`).
- `DOC-2026-03-03-PLAN-RESET-RELEASE-MAP` completed (`done`).

## Changes

- Rebuilt `/Users/andyxu/Documents/project/wherecode/PLAN.md`:
  - active-only format
  - removed historical completed task list
  - added release stage map (`M-TEST-ENTRY -> TST1 -> TST2 -> REL1 -> GO1`)
  - kept current next action as `TST1-T1`
- Rebuilt `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`:
  - active sprint + next sprint view
  - release track table
- Added `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`:
  - stage objective, gate, output, role ownership, immediate run list
- Updated root readmes:
  - `/Users/andyxu/Documents/project/wherecode/README.md`
  - `/Users/andyxu/Documents/project/wherecode/README.zh-CN.md`
  - both now point to `docs/release_map.md`

## Checks

- `bash scripts/check_all.sh`
  - backend tests: `204 passed`
  - command_center build: passed
