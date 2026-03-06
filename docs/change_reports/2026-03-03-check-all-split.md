# 2026-03-03 check_all split

## Scope

- Split monolithic check entry into scoped checks for faster iteration as project count grows.

## Plan update

- `DOC-2026-03-03-CHECK-ALL-SPLIT` started (`doing`).
- `DOC-2026-03-03-CHECK-ALL-SPLIT` completed (`done`).

## Changes

- Added backend-only check script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/check_backend.sh`
- Added command-center-only check script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/check_command_center.sh`
- Updated aggregated check script with scope options:
  - `/Users/andyxu/Documents/project/wherecode/scripts/check_all.sh`
  - scopes: `all|backend|frontend|projects`
  - `all` now runs backend + command_center + standalone project checks
  - standalone project checks auto-discover `project/*/scripts/check.sh`
- Updated scripts docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash scripts/check_all.sh all`
  - backend tests: `205 passed`
  - command_center build: passed
  - standalone projects: no `scripts/check.sh`, skipped
