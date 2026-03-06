# 2026-03-04 TST2 soak checkpoint strict gate fix

## Scope

- Fix strict gate behavior of `tst2_soak_checkpoint.sh` for local tool-session execution.

## Plan update

- `DOC-2026-03-04-TST2-SOAK-CHECKPOINT-STRICT-GATE-FIX` started (`doing`).
- `DOC-2026-03-04-TST2-SOAK-CHECKPOINT-STRICT-GATE-FIX` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_checkpoint.sh`.
  - `--strict` now gates on `guard_passed=true` by default.
  - Added `--require-daemon-running` (and env `SOAK_CHECKPOINT_STRICT_REQUIRE_DAEMON`) for hard daemon-running gate.
  - Added output fields:
    - `strict_mode`
    - `strict_require_daemon_running`
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`.
  - Updated help text for `soak-checkpoint` options.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Documented strict default and daemon requirement flag.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`.
  - Added strict checkpoint gate note.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`.
  - Added hard gate command example with `--require-daemon-running`.

## Validation

- `bash -n scripts/tst2_soak_checkpoint.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh soak-checkpoint --strict`
  - exit code `0`
  - `guard_passed=true`
  - `daemon_running=false`
- `bash scripts/tst2_soak_checkpoint.sh --strict --require-daemon-running`
  - exit code `1` (as expected when daemon not running)
- `bash scripts/stationctl.sh tst2-rehearsal --strict`
  - sandbox run blocked by action-layer bind permission (`127.0.0.1:8100`, `Operation not permitted`)
  - escalated run passed (`overall_passed=true`)
- `bash scripts/stationctl.sh readme-phase-sync --strict`
  - rehearsal note synced to latest strict rehearsal result
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
