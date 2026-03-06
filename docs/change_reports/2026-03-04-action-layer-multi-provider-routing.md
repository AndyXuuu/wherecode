# 2026-03-04 action layer multi provider routing

## Scope

- Add multi-provider routing for action layer real LLM execution.
- Add local model provider support (`ollama`).
- Add real-provider smoke script for runtime verification.

## Plan update

- `DOC-2026-03-04-ACTION-LAYER-MULTI-PROVIDER-ROUTING` started (`doing`).
- `DOC-2026-03-04-ACTION-LAYER-MULTI-PROVIDER-ROUTING` completed (`done`).

## Changes

- Upgraded LLM execution module:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/services/llm_executor.py`
  - Added `LLMRoutingConfig` with:
    - `ACTION_LAYER_LLM_TARGETS_JSON` multi-target config
    - `ACTION_LAYER_LLM_ROUTE_DEFAULT`
    - `ACTION_LAYER_LLM_ROUTE_BY_ROLE_JSON`
    - `ACTION_LAYER_LLM_ROUTE_BY_MODULE_PREFIX_JSON`
  - Added providers:
    - `openai-compatible` (`/v1/chat/completions`)
    - `ollama` (`/api/chat`)
  - Added `RoutedLLMExecutor` for default/role/module-prefix routing.
- Updated action layer runtime for routed providers:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/runtime.py`
  - health/capabilities now include target list and route summary.
- Exported new service symbols:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/services/__init__.py`
- Updated env template:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/.env.example`
- Updated action layer docs:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/README.md`
- Added real-provider smoke script:
  - `/Users/andyxu/Documents/project/wherecode/scripts/action_layer_llm_smoke.sh`
- Updated scripts index:
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
- Reworked unit tests:
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_action_layer_llm_executor.py`
- Synced task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_action_layer_llm_executor.py tests/unit/test_agent_profile_loader.py tests/unit/test_agent_registry.py`
  - `18 passed`
- `bash scripts/check_backend.sh`
  - `222 passed`
- `bash -n scripts/action_layer_llm_smoke.sh action_layer/run.sh scripts/action_layer_smoke.sh`
