# 2026-03-04 action layer system env stationctl

## Scope

- Add system environment file loading for Action Layer runtime.
- Add one-command stationctl entry for real LLM smoke.

## Plan update

- `DOC-2026-03-04-ACTION-LAYER-SYSTEM-ENV-STATIONCTL` started (`doing`).
- `DOC-2026-03-04-ACTION-LAYER-SYSTEM-ENV-STATIONCTL` completed (`done`).

## Changes

- Updated Action Layer runtime launcher:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/run.sh`
  - added system env file loading before local `.env`
  - default source list:
    - `/etc/wherecode/action_layer.env`
    - `$HOME/.wherecode/action_layer.env`
  - override list with `ACTION_LAYER_SYSTEM_ENV_FILES` (`:` separated)
- Updated Action Layer env template:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/.env.example`
  - added `ACTION_LAYER_SYSTEM_ENV_FILES` note
- Updated Action Layer docs:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/README.md`
  - documented env loading order and system config support
- Added stationctl command:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - new command:
    - `action-llm-smoke [action_layer_url] [role] [module_key] [text]`
  - supports `--dry-run`
- Updated scripts index docs:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
- Updated runbook commands:
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - includes `stationctl.sh action-llm-smoke`
  - includes `ACTION_LAYER_SYSTEM_ENV_FILES` usage
- Synced task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n action_layer/run.sh scripts/stationctl.sh scripts/action_layer_llm_smoke.sh scripts/action_layer_smoke.sh`
- `python3 -m py_compile action_layer/services/llm_executor.py action_layer/runtime.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_action_layer_llm_executor.py tests/unit/test_agent_profile_loader.py tests/unit/test_agent_registry.py`
  - `18 passed`
- `bash scripts/check_backend.sh`
  - `222 passed`
