# 2026-03-03 doc consolidation cleanup

## Scope

- Remove outdated docs and duplicate narratives.
- Merge core architecture/role/data info into single spec.
- Keep active docs short and execution-focused.

## Plan update

- `DOC-2026-03-03-DOC-CONSOLIDATION` started (`doing`).
- `DOC-2026-03-03-DOC-CONSOLIDATION` completed (`done`).

## Changes

- Removed old files:
  - `/Users/andyxu/Documents/project/wherecode/CHECKLIST.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/architecture.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/data_model.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/role_orchestration_spec.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/command_center_pencil_spec.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/design_acceptance.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/pencil_app_pages_mapping.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/progress_audit_2026-02-22.md`
- Added merged active specs:
  - `/Users/andyxu/Documents/project/wherecode/docs/system_spec.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/ui_spec.md`
- Rebuilt active docs:
  - `/Users/andyxu/Documents/project/wherecode/docs/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/oncall_checklist.md`
- Updated references:
  - `/Users/andyxu/Documents/project/wherecode/docs/protocol.md`
  - `/Users/andyxu/Documents/project/wherecode/command_center/README.md`
- Compacted root readmes:
  - `/Users/andyxu/Documents/project/wherecode/README.md`
  - `/Users/andyxu/Documents/project/wherecode/README.zh-CN.md`

## Checks

- `bash scripts/check_all.sh`
  - backend tests: `204 passed`
  - command_center build: passed
