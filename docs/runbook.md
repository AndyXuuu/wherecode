# Runbook (Active) / 运行手册（当前）

Updated: 2026-03-06

## 1) Standard command entry / 标准命令入口

Use root scripts. Do not install mixed dependencies at repository root.  
使用根目录脚本。不要在仓库根目录混装依赖。

Cadence rule / 执行节奏规则:
- Daily development: run `quick` only / 日常开发只跑 `quick`。
- Gate/release phase: run `full` and `release` / 门禁与发布阶段跑 `full` 与 `release`。

```bash
bash scripts/stationctl.sh install all
bash scripts/stationctl.sh dev all
bash scripts/stationctl.sh start all
bash scripts/stationctl.sh status all
bash scripts/stationctl.sh stop all
bash scripts/stationctl.sh check
bash scripts/stationctl.sh check quick
bash scripts/stationctl.sh check release
bash scripts/check_backend.sh quick
bash scripts/check_backend.sh full
bash scripts/check_all.sh quick
bash scripts/check_all.sh release
bash scripts/stationctl.sh soak start
bash scripts/stationctl.sh soak status --strict
bash scripts/stationctl.sh soak stop
bash scripts/stationctl.sh soak-checkpoint --strict
bash scripts/stationctl.sh tst2-rehearsal
bash scripts/stationctl.sh tst2-rehearsal --strict
bash scripts/stationctl.sh tst2-rehearsal-latest
bash scripts/stationctl.sh tst2-progress --profile full
bash scripts/stationctl.sh tst2-progress --profile local
bash scripts/stationctl.sh tst2-watch --profile full --interval 60 --max-rounds 10
bash scripts/stationctl.sh tst2-autopilot --profile full --watch-interval 60 --watch-max-rounds 120
bash scripts/stationctl.sh mb3-dry-run
bash scripts/stationctl.sh action-llm-check http://127.0.0.1:8100
bash scripts/stationctl.sh readme-phase-sync --strict
```

## 2) Minimal env baseline / 最小环境基线

```bash
export WHERECODE_TOKEN=change-me
export WHERECODE_STATE_BACKEND=sqlite
export WHERECODE_SQLITE_PATH=.wherecode/state.db
export ACTION_LAYER_REQUIRE_LLM=true
export ACTION_LAYER_EXECUTION_MODE=llm
```

Optional / 可选项:

```bash
export WHERECODE_RELEASE_APPROVAL_REQUIRED=true
export WHERECODE_AGENT_ROUTING_FILE=control_center/agents.routing.json
export WHERECODE_COMMAND_ORCHESTRATE_POLICY_ENABLED=true
export WHERECODE_COMMAND_ORCHESTRATE_PREFIXES="/orchestrate,orchestrate:,编排:,主流程:"
export WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES=6
export WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_STRATEGY=balanced
export WHERECODE_DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK=true
export OPENAI_API_KEY=your-key
```

Action Layer can also load system env files (loaded by `action_layer/run.sh`).  
Action Layer 也可读取系统环境配置文件（由 `action_layer/run.sh` 加载）：

```bash
export ACTION_LAYER_SYSTEM_ENV_FILES="/etc/wherecode/action_layer.env:$HOME/.wherecode/action_layer.env"
```

If `ACTION_LAYER_REQUIRE_LLM=true` and model config is missing, `action_layer` fails fast on startup.  
如果 `ACTION_LAYER_REQUIRE_LLM=true` 且模型配置缺失，`action_layer` 启动会直接失败（符合 AI 必需策略）。

## 3) Health and contract checks / 健康与契约检查

```bash
curl http://127.0.0.1:8000/healthz
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/action-layer/health
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/metrics/summary
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/metrics/workflows
control_center/.venv/bin/pytest -q
bash scripts/check_backend.sh full
bash scripts/check_all.sh quick
bash scripts/check_all.sh release
```

If API schema changed / 如果 API 契约变更:

```bash
control_center/.venv/bin/python scripts/update_openapi_snapshot.py
control_center/.venv/bin/pytest -q
```

## 4) Verification and rehearsal set / 验证与演练集合

```bash
bash scripts/action_layer_llm_check.sh http://127.0.0.1:8100
bash scripts/stationctl.sh action-llm-check http://127.0.0.1:8100
bash scripts/mb3_dry_run_seed.sh
bash scripts/stationctl.sh mb3-dry-run
bash scripts/check_backend.sh quick
bash scripts/check_all.sh quick
bash scripts/check_backend.sh full
bash scripts/check_all.sh release
bash scripts/v3_recovery_drill.sh
bash scripts/v3_parallel_probe.sh http://127.0.0.1:8000 6 3
bash scripts/ci_v3_rehearsal.sh
SOAK_DURATION_SECONDS=86400 SOAK_INTERVAL_SECONDS=300 bash scripts/tst2_soak.sh
bash scripts/tst2_soak_status.sh --strict
bash scripts/tst2_soak_daemon.sh start
bash scripts/tst2_soak_daemon.sh status --strict
bash scripts/tst2_soak_daemon.sh stop
bash scripts/tst2_soak_checkpoint.sh --strict
bash scripts/stationctl.sh soak start
bash scripts/stationctl.sh soak status --strict
bash scripts/stationctl.sh soak stop
bash scripts/stationctl.sh soak-checkpoint --strict
bash scripts/tst2_t2_release_rehearsal.sh
bash scripts/stationctl.sh tst2-rehearsal
bash scripts/stationctl.sh tst2-rehearsal-latest
```

Note: `tst2_soak_daemon.sh start` will resume the latest unfinished soak samples automatically.  
说明：`tst2_soak_daemon.sh start` 会自动续跑最近未完成的 soak 样本。
Note: `tst2_soak_checkpoint.sh --strict` gates on `guard_passed` by default; add `--require-daemon-running` if needed.  
说明：`tst2_soak_checkpoint.sh --strict` 默认按 `guard_passed` 门禁；如需可加 `--require-daemon-running`。
Note: `mb3_dry_run_seed.sh` writes run evidence to `docs/ops_reports/latest_mb3_dry_run_seed.json`.  
说明：`mb3_dry_run_seed.sh` 会把主流程演练证据写入 `docs/ops_reports/latest_mb3_dry_run_seed.json`。
Note: if command terminal status is non-success but `workflow_run_id` exists, treat it as valid dry-run evidence and use `primary_recovery_action`.  
说明：若 command 终态非 success 但存在 `workflow_run_id`，仍可作为有效 dry-run 证据，并按 `primary_recovery_action` 继续恢复流程。

Milestone gate / 里程碑门禁:

```bash
bash scripts/v3_milestone_gate.sh --milestone test-entry --strict
bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict
bash scripts/v3_milestone_gate.sh --milestone tst2-ready --tst2-profile local --strict
```

## 5) Metrics and policy operations / 指标与策略操作

```bash
bash scripts/v3_metrics_report.sh
bash scripts/v3_metrics_alert_check.sh
bash scripts/v3_metrics_policy_rollback.sh <audit_id> --dry-run
bash scripts/v3_metrics_rollback_approval_gc.sh --dry-run
```

Policy API / 策略接口:

```bash
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  http://127.0.0.1:8000/metrics/workflows/alert-policy
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  http://127.0.0.1:8000/metrics/workflows/alert-policy/audits?limit=20
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  http://127.0.0.1:8000/metrics/workflows/alert-policy/rollback-approvals/stats
```

## 6) Command orchestrate policy quick path / 指令编排策略快速路径

Command entry examples / 指令入口示例:

```bash
/orchestrate build crawl and sentiment pipeline --module-hints=crawl,sentiment --strategy=balanced --execute=false
/orchestrate build report pipeline --max-modules=4 --execute=true --confirmed-by=owner
```

Workflow API checks / 主流程接口检查:

```bash
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  http://127.0.0.1:8000/v3/workflows/runs/<run_id>/orchestrate/latest
curl -X POST -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" -H "Content-Type: application/json" \
  -d '{"action":"reconfirm_decomposition","confirmed_by":"owner"}' \
  http://127.0.0.1:8000/v3/workflows/runs/<run_id>/orchestrate/recover
```

MB3 recovery follow-up / MB3 恢复动作跟进:

```bash
RUN_ID="$(python3 -c 'import json; print(json.load(open("docs/ops_reports/latest_mb3_dry_run_seed.json"))["workflow_run_id"])')"
curl -X POST -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" -H "Content-Type: application/json" \
  -d '{"action":"retry_with_decompose_payload","strategy":"balanced","requirements":"build stock sentiment pipeline with opinion crawl sentiment scoring and industry theme analysis","module_hints":["crawl","sentiment","theme","industry"],"max_modules":6,"requested_by":"mb3-recover","execute":false}' \
  "http://127.0.0.1:8000/v3/workflows/runs/${RUN_ID}/orchestrate/recover"
```

## 7) References / 参考链接

- Full script flags: `scripts/README.md`
- System roles and state model: `docs/system_spec.md`
- Active release path: `docs/release_map.md`
- Task board: `docs/v3_task_board.md`
- Troubleshooting: `docs/troubleshooting.md`
