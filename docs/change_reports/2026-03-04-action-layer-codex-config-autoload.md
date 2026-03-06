# 2026-03-04 action layer codex config autoload

## Plan

- `DOC-2026-03-04-ACTION-LAYER-CODEX-CONFIG-AUTOLOAD` started (`doing`)
- `DOC-2026-03-04-ACTION-LAYER-CODEX-CONFIG-AUTOLOAD` completed (`done`)

## Changes

- Added Codex system config fallback in Action Layer bootstrap:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/run.sh`
- New behavior:
  - auto-read `${CODEX_HOME:-$HOME/.codex}/config.toml`
  - auto-read `${CODEX_HOME:-$HOME/.codex}/auth.json`
  - populate missing `ACTION_LAYER_*` runtime vars without overriding existing explicit values
- Added optional runtime controls:
  - `ACTION_LAYER_USE_CODEX_CONFIG` (default `true`)
  - `ACTION_LAYER_CODEX_CONFIG_PATH`
  - `ACTION_LAYER_CODEX_AUTH_PATH`
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/README.md`
  - `/Users/andyxu/Documents/project/wherecode/action_layer/.env.example`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_action_layer_llm_executor.py`
  - `8 passed`
- `bash scripts/check_backend.sh`
  - `227 passed`
