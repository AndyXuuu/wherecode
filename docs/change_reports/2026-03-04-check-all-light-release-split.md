# 2026-03-04 check all light release split

## Scope

- Simplify default check strategy for single-machine workflow.
- Keep heavy checks available for release stage.

## Plan update

- `DOC-2026-03-04-CHECK-ALL-LIGHT-RELEASE-SPLIT` started (`doing`).
- `DOC-2026-03-04-CHECK-ALL-LIGHT-RELEASE-SPLIT` completed (`done`).

## Changes

- Updated unified check entry:
  - `/Users/andyxu/Documents/project/wherecode/scripts/check_all.sh`
  - new default scope: `dev`
  - new scopes:
    - `dev`: backend + action-layer llm smoke
    - `release`: dev + command_center build + project checks
    - `all`: alias of `release` (legacy compatibility)
    - `llm`: action-layer llm smoke only
  - added llm gate env overrides:
    - `CHECK_ALL_ACTION_LAYER_URL`
    - `CHECK_ALL_LLM_ROLE`
    - `CHECK_ALL_LLM_MODULE_KEY`
    - `CHECK_ALL_LLM_TEXT`
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/troubleshooting.md`
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md` (gate command baseline adjusted)
- Synced task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/check_all.sh scripts/stationctl.sh scripts/action_layer_llm_smoke.sh`
- `bash scripts/check_all.sh backend`
  - backend pytest: `224 passed`
- `bash scripts/check_all.sh help`
