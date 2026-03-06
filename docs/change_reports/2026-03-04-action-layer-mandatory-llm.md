# 2026-03-04 action layer mandatory llm

## Scope

- Enforce AI/LLM as mandatory runtime requirement for Action Layer.
- Remove default mock-first behavior.

## Plan update

- `DOC-2026-03-04-ACTION-LAYER-MANDATORY-LLM` started (`doing`).
- `DOC-2026-03-04-ACTION-LAYER-MANDATORY-LLM` completed (`done`).

## Changes

- Enforced LLM-required policy in config loader:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/services/llm_executor.py`
  - default mode switched to `llm`
  - when `ACTION_LAYER_REQUIRE_LLM=true`, `mock` mode is rejected at config stage
- Enforced startup/runtime checks:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/runtime.py`
  - startup exits non-zero when LLM is required but not ready
  - `/healthz` reports `status=error` when required LLM is unavailable
  - `/execute` returns `503` when required LLM is unavailable
- Updated env defaults:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/.env.example`
  - `ACTION_LAYER_REQUIRE_LLM=true`
  - `ACTION_LAYER_EXECUTION_MODE=llm`
  - kept explicit diagnostic-only mock example
- Improved stationctl start behavior:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - service start now verifies process remains alive; early exit is treated as startup failure with log tail
- Updated docs:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/README.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/runbook.md`
  - `/Users/andyxu/Documents/project/wherecode/scripts/README.md`
- Added policy tests:
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_action_layer_llm_executor.py`
  - mock rejected when LLM required
  - mock allowed only when explicitly disabling LLM requirement
- Synced task log:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n action_layer/run.sh scripts/stationctl.sh scripts/action_layer_llm_smoke.sh scripts/action_layer_smoke.sh`
- `python3 -m py_compile action_layer/services/llm_executor.py action_layer/runtime.py`
- `control_center/.venv/bin/pytest -q tests/unit/test_action_layer_llm_executor.py tests/unit/test_agent_profile_loader.py tests/unit/test_agent_registry.py`
  - `20 passed`
- `bash scripts/check_backend.sh`
  - `224 passed`
