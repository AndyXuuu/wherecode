## Scope

- Align provider runtime with local Codex config (`~/.codex/config.toml` + `auth.json`) and add `wire_api` support (`chat_completions` / `responses`).
- Fix provider execute failure root causes:
  - add explicit `User-Agent` for action-layer HTTP requests (avoid upstream 403/1010 on default urllib UA),
  - add retry for transient provider/network failures (5xx / URL errors),
  - raise control-center action-layer timeout (default `30s`) to match real LLM latency.
- Harden GO4 validation tooling:
  - `scripts/go4_provider_probe.sh` uses codex defaults + `wire_api` + explicit `--url` / `--data-binary`,
  - `scripts/v3_recovery_drill.sh` supports multi-round discussion/approval unblocking and bash3 compatibility.
- Close GO4 milestone docs (`PLAN`, `task_board`, `release_map`, bilingual `README`).

## Changed Files

- `action_layer/services/llm_executor.py`
- `action_layer/run.sh`
- `action_layer/.env.example`
- `action_layer/README.md`
- `control_center/services/action_layer_client.py`
- `control_center/main.py`
- `control_center/.env.example`
- `control_center/README.md`
- `scripts/go4_provider_probe.sh`
- `scripts/v3_recovery_drill.sh`
- `tests/unit/test_action_layer_llm_executor.py`
- `PLAN.md`
- `docs/v3_task_board.md`
- `docs/release_map.md`
- `README.md`
- `README.zh-CN.md`

## Validation

- `control_center/.venv/bin/pytest -q tests/unit/test_action_layer_llm_executor.py` -> `9 passed`.
- `bash scripts/go4_provider_probe.sh` -> provider runtime probe `200` (`docs/ops_reports/20260306T152313Z-go4-provider-probe.json`).
- `bash scripts/action_layer_llm_check.sh` -> pass (`status in {success, needs_discussion}`).
- `bash scripts/action_layer_llm_smoke.sh` -> pass (`status in {success, needs_discussion}`).
- `bash scripts/v3_recovery_drill.sh` -> pass (`run_id=wfr_501721f2085e`, `gates=4`, `artifacts=3`).
