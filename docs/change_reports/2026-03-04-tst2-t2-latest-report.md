# 2026-03-04 tst2-t2 latest report

## Scope

- Add stable latest-entry files for TST2-T2 rehearsal outputs.

## Plan update

- `DOC-2026-03-04-TST2-T2-LATEST-REPORT` started (`doing`).
- `DOC-2026-03-04-TST2-T2-LATEST-REPORT` completed (`done`).

## Changes

- Enhanced TST2-T2 rehearsal script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_t2_release_rehearsal.sh`
  - after each run writes:
    - `docs/ops_reports/latest_tst2_t2_release_rehearsal.md`
    - `docs/ops_reports/latest_tst2_t2_release_rehearsal.json`
- Added latest-report reader:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_t2_rehearsal_latest.sh`
  - supports:
    - `--path-only`
    - `--strict`
  - fallback behavior:
    - if latest file missing, copy newest `*-tst2-t2-release-rehearsal.md` into latest entry
- Added stationctl entry:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - `bash scripts/stationctl.sh tst2-rehearsal-latest`
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/README.md`
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/tst2_t2_release_rehearsal.sh scripts/tst2_t2_rehearsal_latest.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh --dry-run tst2-rehearsal --strict`
- `bash scripts/stationctl.sh tst2-rehearsal`
- `bash scripts/stationctl.sh tst2-rehearsal-latest`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - project backend tests: `1 passed`
