# 2026-03-04 TST2 soak checkpoint tooling

## Scope

- Add checkpoint status script for live TST2 soak monitoring.
- Integrate checkpoint command into runbook/release/oncall docs.

## Plan update

- `DOC-2026-03-04-TST2-SOAK-CHECKPOINT` started (`doing`).
- `DOC-2026-03-04-TST2-SOAK-CHECKPOINT` completed (`done`).

## Changes

- Added script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_status.sh`
  - features:
    - auto-detect latest `*-tst2-soak-samples.jsonl`
    - compute failed-run drift, peaks, probe pass/fail, sample staleness
    - `--strict` exits non-zero if guard fails
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/oncall_checklist.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
- Updated active tracking:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
  - `/Users/andyxu/Documents/project/wherecode/.wherecode/state.json`

## Checks

- `bash -n scripts/tst2_soak_status.sh`
- `bash scripts/tst2_soak_status.sh --strict`
  - latest status: `samples_total=2`, `guard_passed=true`
- `bash scripts/check_all.sh`
  - backend tests: `205 passed`
  - command_center build: passed
