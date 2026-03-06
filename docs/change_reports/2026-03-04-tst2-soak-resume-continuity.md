# 2026-03-04 TST2 soak resume continuity

## Scope

- Make TST2 soak data collection resumable across daemon restarts.

## Plan update

- `DOC-2026-03-04-TST2-SOAK-RESUME-CONTINUITY` started (`doing`).
- `DOC-2026-03-04-TST2-SOAK-RESUME-CONTINUITY` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak.sh`.
  - Added optional env overrides:
    - `SOAK_SAMPLES_PATH`
    - `SOAK_PROBE_LOG_PATH`
    - `SOAK_SUMMARY_PATH`
  - If samples file already exists, reads existing rounds and continues from next round.
  - If target rounds already reached, regenerates summary only (no duplicate sampling).
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_daemon.sh`.
  - Added `--report-dir <path>` (`TST2_SOAK_REPORT_DIR`) support.
  - `start` now detects latest unfinished soak samples and resumes on same files.
  - Start metadata now records resume source and existing rounds.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Documented auto-resume behavior.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`.
  - Added `readme-phase-sync` command entry and soak auto-resume note.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`.
  - Added auto-resume note under tool-session soak issue.

## Validation

- `bash -n scripts/tst2_soak.sh scripts/tst2_soak_daemon.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh soak start`
  - resumed `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260304T130928Z-tst2-soak-samples.jsonl`
  - round advanced to `7/288`
- `bash scripts/stationctl.sh soak status --strict` passed
- `bash scripts/stationctl.sh soak stop`
- `bash scripts/stationctl.sh soak-checkpoint --strict`
  - guard passed but strict gate still returned non-zero (`daemon_running=false` in tool session)
- `bash scripts/check_all.sh all` passed
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
