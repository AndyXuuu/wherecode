# 2026-03-03 TST2 soak automation and rehearsal

## Scope

- Add automation script for `TST2-T1` stability soak and drift sampling.
- Run short soak rehearsal and record artifacts.
- Update active plan/state/docs to reflect `TST2-T1` progress.

## Plan update

- `TST2-T1` soak automation started (`doing`).
- `TST2-T1` soak rehearsal completed (`done`).
- `TST2-T1` blocked: waiting 24h wall-clock soak window.
- `TST2-T1` blocked: 24h background soak process not persistent in tool session.
- `TST2-T1` 24h soak live session started (`doing`).

## Changes

- Added script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak.sh`
  - features:
    - service bootstrap/wait
    - periodic metrics sampling to JSONL
    - optional per-round parallel probe
    - drift guard on failed-run delta
    - markdown summary output
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
- Added TST2 soak evidence:
  - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T134206Z-tst2-soak-summary.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T134206Z-tst2-soak-samples.jsonl`
  - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T134206Z-tst2-soak-probe.log`
  - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/2026-03-03-tst2-t1-soak-rehearsal.md`
  - live 24h run artifacts (in progress):
    - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T135333Z-tst2-soak-samples.jsonl`
    - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T135333Z-tst2-soak-probe.log`
    - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T135333Z-tst2-soak-summary.md` (generated on completion)
- Updated active state:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`
  - `/Users/andyxu/Documents/project/wherecode/.wherecode/state.json`

## Checks

- `bash -n scripts/tst2_soak.sh`
- short soak rehearsal:
  - `SOAK_DURATION_SECONDS=60 SOAK_INTERVAL_SECONDS=20 SOAK_PROBE_RUN_COUNT=2 SOAK_PROBE_WORKERS=1 SOAK_RUN_PROBE_EACH_ROUND=true bash scripts/tst2_soak.sh`
- 24h soak start attempt:
  - `SOAK_DURATION_SECONDS=86400 ... bash scripts/tst2_soak.sh` (background process exited with no persistent runner in tool session)
- live 24h soak session started:
  - `SOAK_DURATION_SECONDS=86400 SOAK_INTERVAL_SECONDS=300 ... bash scripts/tst2_soak.sh`
- `bash scripts/check_all.sh`
  - backend tests: `205 passed`
  - command_center build: passed
