# 2026-03-04 README phase sync automation

## Scope

- Automate README `Plan & Completed Phases` sync from current `PLAN.md` state.

## Plan update

- `DOC-2026-03-04-README-PHASE-SYNC-AUTOMATION` started (`doing`).
- `DOC-2026-03-04-README-PHASE-SYNC-AUTOMATION` completed (`done`).

## Changes

- Added `/Users/andyxu/Documents/project/wherecode/scripts/readme_phase_sync.sh`.
  - Rebuilds README section `## 📅 Plan & Completed Phases` from:
    - `PLAN.md` Active Sprint table
    - `PLAN.md` Release Map table
    - optional `docs/ops_reports/latest_tst2_t2_release_rehearsal.json` note for `TST2-T2`
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`.
  - Added command: `readme-phase-sync [--dry-run] [--strict]`
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Added script and entrypoint usage.
- Updated `/Users/andyxu/Documents/project/wherecode/README.MD`.
  - Synced only `Plan & Completed Phases` section.

## Checks

- `bash -n scripts/readme_phase_sync.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh readme-phase-sync --strict`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
