# 2026-03-05 remove legacy validation flows

## Plan

- `DOC-2026-03-05-REMOVE-LEGACY-VALIDATION-FLOWS` started (`doing`)
- `DOC-2026-03-05-REMOVE-LEGACY-VALIDATION-FLOWS` completed (`done`)

## Changes

- Removed legacy validation checks from active script entrypoints:
  - `scripts/check_all.sh`
  - `scripts/ci_v3_rehearsal.sh`
- Added new LLM check entry and command:
  - `scripts/action_layer_llm_check.sh`
  - `scripts/stationctl.sh` (`action-llm-check`)
- Updated active plan/release/runbook/troubleshooting docs to check terminology and non-legacy command sets:
  - `PLAN.md`
  - `docs/README.md`
  - `docs/release_map.md`
  - `docs/runbook.md`
  - `docs/troubleshooting.md`
  - `scripts/README.md`

## Checks

- `bash -n scripts/check_all.sh scripts/ci_v3_rehearsal.sh scripts/stationctl.sh scripts/action_layer_llm_check.sh`
- `bash scripts/check_all.sh backend`
  - `236 passed`
- `bash scripts/check_all.sh dev`
  - `236 passed`
- `bash scripts/check_all.sh release`
  - backend `236 passed`
  - command_center build passed
  - project checks passed
