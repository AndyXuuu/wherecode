# 2026-03-04 action layer real llm

## Scope

- Add real LLM execution path in `action_layer` while keeping mock fallback.

## Plan update

- `DOC-2026-03-04-ACTION-LAYER-REAL-LLM` started (`doing`).
- `DOC-2026-03-04-ACTION-LAYER-REAL-LLM` completed (`done`).

## Changes

- Added OpenAI-compatible provider executor and config loader:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/services/llm_executor.py`
  - supports env-driven `mock|llm` mode selection
  - validates required vars for `mode=llm`
  - calls `POST /v1/chat/completions`
  - parses model JSON output into action protocol
  - auto fallback for non-JSON model output
- Exported provider classes in service package:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/services/__init__.py`
- Wired runtime to select mock or real provider execution:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/runtime.py`
  - health/capabilities now expose mode/provider/readiness
  - `execute` keeps role-profile guard and discussion short-circuit
  - llm errors mapped to protocol `failed` response with metadata
- Added action layer env template for real LLM:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/.env.example`
- Updated action layer usage docs:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/README.md`
- Added unit tests for config/parse/fallback/error paths:
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_action_layer_llm_executor.py`
- Synced task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_action_layer_llm_executor.py tests/unit/test_agent_profile_loader.py tests/unit/test_agent_registry.py`
  - `16 passed`
- `bash scripts/check_backend.sh`
  - `220 passed`
