# 2026-03-04 TST2 milestone profile

## Scope

- Add `tst2-ready` gate profile support to keep strict release gate unchanged while enabling local full-flow validation.

## Plan update

- `DOC-2026-03-04-TST2-MILESTONE-PROFILE` started (`doing`).
- `DOC-2026-03-04-TST2-MILESTONE-PROFILE` completed (`done`).

## Changes

- Updated `/Users/andyxu/Documents/project/wherecode/scripts/v3_milestone_gate.sh`.
  - Added `--tst2-profile <full|local>` (`TST2_PROFILE`, default `full`).
  - `full` keeps strict defaults (`min_samples=288`, `duration=86400`, `interval=300`).
  - `local` default thresholds:
    - `min_samples=12`
    - `duration=2400`
    - `interval=300`
    - `max_failed_run_delta=0`
    - `max_probe_failed_rounds=0`
  - Explicit threshold flags still override profile defaults.
  - Gate output now includes profile in `required/observed`.
  - `local` pass summary text: `TST2 local readiness reached`.
- Updated `/Users/andyxu/Documents/project/wherecode/scripts/README.md`.
  - Documented profile semantics and options.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`.
  - Added local profile milestone command example.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/release_map.md`.
  - Added local profile command in immediate run list.
- Updated `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`.
  - Added local profile fallback command for flow validation.
- Updated `/Users/andyxu/Documents/project/wherecode/PLAN.md`.
  - Added profile task completion and latest full/local gate snapshot.

## Validation

- `bash -n scripts/v3_milestone_gate.sh`
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`
  - blocked as expected with `tst2_profile=full` (`rc=1`)
- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --tst2-profile local --strict`
  - passed (`rc=0`)
  - `next_phase=REL1`
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - standalone project checks: passed
