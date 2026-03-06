# 2026-03-04 TST2 milestone gate

## Scope

- Add executable milestone gate for `TST2` readiness to avoid endless soak loop.

## Plan update

- `DOC-2026-03-04-TST2-MILESTONE-GATE` started (`doing`).
- `DOC-2026-03-04-TST2-MILESTONE-GATE` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/v3_milestone_gate.sh`.
  - Added milestone `tst2-ready`.
  - `tst2-ready` checks:
    - soak samples existence
    - minimum samples threshold (default `288`)
    - soak coverage threshold (default `86400-300=86100` seconds)
    - failed run delta threshold (default `<=0`)
    - probe failure rounds threshold (default `<=0`)
    - latest rehearsal summary exists and `overall_passed=true`
    - latest rehearsal checkpoint guard passed
  - Added options:
    - `--soak-samples-file`
    - `--tst2-summary-file`
    - `--tst2-min-samples`
    - `--tst2-duration-seconds`
    - `--tst2-interval-seconds`
    - `--tst2-max-failed-run-delta`
    - `--tst2-max-probe-failed-rounds`
- Updated `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`.
  - TST2 gate command now uses milestone gate.
  - Immediate run list added `tst2-ready` gate command.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`.
  - Added `tst2-ready` gate command in milestone section.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`.
  - Added section for `tst2-ready` gate blocked troubleshooting.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Added `tst2-ready` milestone documentation and options.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Added TST2 milestone gate task log and latest blocked reason snapshot.

## Validation

- `bash -n scripts/v3_milestone_gate.sh`
- `bash scripts/v3_milestone_gate.sh --milestone test-entry --strict`
  - blocked as expected with current `.wherecode/state.json` (`rc=1`)
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`
  - blocked as expected (`rc=1`)
  - missing: `soak_samples_reached_minimum`, `soak_coverage_reached_seconds`
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready`
  - produced machine-readable blocked payload
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
