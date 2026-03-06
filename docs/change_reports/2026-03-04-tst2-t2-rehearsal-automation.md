# 2026-03-04 tst2-t2 rehearsal automation

## Scope

- Add one-command TST2-T2 flow: release rehearsal + rollback drill + checkpoint.

## Plan update

- `DOC-2026-03-04-TST2-T2-REHEARSAL-AUTOMATION` started (`doing`).
- `DOC-2026-03-04-TST2-T2-REHEARSAL-AUTOMATION` completed (`done`).

## Changes

- Added TST2-T2 orchestration script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_t2_release_rehearsal.sh`
  - flow:
    1. run `ci_v3_rehearsal.sh`
    2. fetch latest policy audit id
    3. run `v3_metrics_policy_rollback.sh <audit_id> --dry-run`
    4. run `stationctl soak-checkpoint`
  - outputs report + logs:
    - `docs/ops_reports/<timestamp>-tst2-t2-release-rehearsal.md`
    - `docs/ops_reports/<timestamp>-tst2-t2-ci-rehearsal.log`
    - `docs/ops_reports/<timestamp>-tst2-t2-rollback-drill.log`
  - supports:
    - `--strict`
    - `--dry-run`
- Added stationctl command:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - `bash scripts/stationctl.sh tst2-rehearsal [--strict]`
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/tst2_t2_release_rehearsal.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh --dry-run tst2-rehearsal --strict`
- `bash scripts/stationctl.sh tst2-rehearsal`
  - report: `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260304T131851Z-tst2-t2-release-rehearsal.md`
  - overall: `overall_passed=true`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - project backend tests: `1 passed`
