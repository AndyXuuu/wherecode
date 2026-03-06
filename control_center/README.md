# Control Center 说明

本目录是 WhereCode 的执行中枢（Control Center），负责 API、会话、路由和任务编排。
通信模式为 HTTP 异步：提交命令后返回 `202`，客户端通过轮询获取执行状态。
同时对 Action Layer 提供统一代理接口：

- `GET /action-layer/health`
- `POST /action-layer/execute`
- `GET /metrics/summary`（运行指标聚合）
- `GET /agent-routing`（查看当前路由规则）
- `PUT /agent-routing`（更新路由规则）
- `POST /agent-routing/reload`（热重载路由规则）

V3 workflow decomposition confirmation flow:

- `POST /v3/workflows/runs/{run_id}/decompose-bootstrap`
- `GET /v3/workflows/runs/{run_id}/decompose-bootstrap/pending`
- `GET /v3/workflows/runs/{run_id}/decompose-bootstrap/status`
- `POST /v3/workflows/runs/{run_id}/decompose-bootstrap/advance`
- `POST /v3/workflows/runs/{run_id}/decompose-bootstrap/advance-loop`
- `POST /v3/workflows/runs/{run_id}/orchestrate`
- `GET /v3/workflows/runs/{run_id}/orchestrate/latest`
- `POST /v3/workflows/runs/{run_id}/orchestrate/recover`
- `GET /v3/workflows/runs/{run_id}/decompose-bootstrap/preview`
- `POST /v3/workflows/runs/{run_id}/decompose-bootstrap/confirm`
- `POST /v3/workflows/runs/{run_id}/execute`（pending confirmation 时返回 `409`）

Decompose bootstrap execution contract:

- chief 返回的 `module_task_packages` 会直接用于创建模块 workitems（不再只用固定模板链路）。
- task item 必填：`role`、`objective`。
- task item 可选：`depends_on_roles`（模块内依赖）、`deliverable`、`priority`。
- 若未提供 `depends_on_roles`，默认按任务包顺序串行依赖；提供后可表达模块内并行/串行混合拓扑。
- 可通过 preview API 读取执行前编排视图（任务 key、依赖、并行分组、terminal task）。
- preview API 支持 `?refresh=true` 强制重算；默认优先返回指纹命中的缓存快照。
- 预览快照写入 run metadata：`decompose_bootstrap_preview`（`fingerprint` + `payload`）。
- preview 响应包含 `cache_hit`、`cache_fingerprint`，便于前端区分缓存命中/重算。
- pending API 会返回 preview 状态（`preview_ready`/`preview_stale`/`preview_generated_at`/`preview_fingerprint`）。
- status API 聚合返回：decomposition 来源、确认状态、preview 状态、workitem 分布、`next_action`。
- advance API 会基于 `next_action` 自动推进一轮（preview/confirm/bootstrap/execute/tick）。
- 当 `next_action=confirm_or_reject_decomposition` 时，advance 请求需提供 `confirmed_by`。
- advance-loop API 会连续推进多步，直到 blocked/noop/bootstrap finished/达到 max_steps。
- execute API 默认启用 `auto_advance_decompose=true`，会先走 advance-loop，再执行 workflow run。
- execute API 可透传自动推进参数：`decompose_confirmed_by`、`auto_advance_max_steps`、`auto_advance_execute_max_loops`。
- orchestrate API 提供单入口：按需 decompose（缺失或强制重分解）并可直接 execute。
- orchestrate API 支持 `decompose_payload` 模板（`requirements/module_hints/max_modules/requested_by`）。
- orchestrate API 支持 `strategy=speed|balanced|safe`：`balanced/safe` 会收敛 auto-advance 步数，`safe` 强制 refresh preview。
- orchestrate 响应包含 `decomposition_summary`（模块数、任务角色分布、覆盖标签、确认/预览状态、next_action）。
- orchestrate 响应包含 `decision_report`：`human_summary`（简洁文本）+ `machine`（结构化字段）。
- `decision_report.machine` 包含恢复建议：`primary_recovery_action` + `recovery_actions`（retry/refresh/reconfirm 候选）。
- `decision_report.machine` 新增评分：`primary_recovery_priority`、`primary_recovery_confidence`、`scored_recovery_actions`。
- `decision_report.machine.execution_profile` 回显策略生效后的执行参数（loops/auto_steps/force_refresh）。
- orchestrate 响应包含 `telemetry_snapshot`：编排耗时、workitem 增量、unfinished 增量、next_action 迁移、execute 结果摘要。
- orchestrate latest API 返回该 run 最近一次编排记录（strategy/status/actions/reason/decision/telemetry）。
- orchestrate recover API 支持执行恢复动作（可显式指定 action，或使用 latest primary recovery action）。
- command API 支持编排触发策略：命令前缀命中（默认如 `/orchestrate`）时自动创建 workflow run 并调用 orchestrate。
- command 编排执行结果会写入 command metadata（`command_execution_mode`、`workflow_run_id`、`orchestration_status`）。
- command 编排策略会同步持久化 `workflow_state_latest` 到 command/task/run metadata（含 `next_action` 与 `primary_recovery_action`）。
- command 编排策略支持 flags：`--strategy`、`--module-hints`、`--max-modules`、`--execute`、`--force-redecompose`、`--confirmed-by` 等。
- command 编排示例：`/orchestrate build crawl pipeline --module-hints=crawl,sentiment --strategy=balanced --execute=false`

## 目录结构

- `main.py`: FastAPI 应用入口（当前提供 `/healthz`）
- `requirements.txt`: Control Center Python 依赖
- `.env.example`: Control Center 环境变量示例
- `run.sh`: Control Center 本地启动脚本
- `api/`: HTTP 异步接口层
- `core/`: 配置、鉴权、通用基础能力
- `models/`: Pydantic 数据模型（已包含项目->任务->命令层级结构）
- `services/`: 业务服务层（会话、任务、通知）
- `../action_layer/`: Agent 抽象与实现（Action Layer）

## 环境变量

- `WHERECODE_AUTH_ENABLED`：是否开启鉴权，默认 `true`
- `WHERECODE_TOKEN`：Control Center API token，默认 `change-me`
- `WHERECODE_ALLOWED_ORIGINS`：CORS 白名单，默认 `http://localhost:3000`
- `ACTION_LAYER_BASE_URL`：Action Layer 代理地址，默认 `http://127.0.0.1:8100`
- `ACTION_LAYER_TIMEOUT_SECONDS`：Action Layer 调用超时秒数，默认 `30`
- `WHERECODE_STATE_BACKEND`：状态存储后端，`memory` 或 `sqlite`（默认 `memory`）
- `WHERECODE_SQLITE_PATH`：SQLite 文件路径（默认 `.wherecode/state.db`）
- `WHERECODE_AGENT_ROUTING_FILE`：智能体路由规则文件（默认 `control_center/agents.routing.json`）
- `WHERECODE_DECOMPOSE_REQUIRE_EXPLICIT_MAP`：`decompose-bootstrap` 是否强制要求主脑返回需求点->模块映射（默认 `true`）
- `WHERECODE_DECOMPOSE_REQUIRE_TASK_PACKAGE`：`decompose-bootstrap` 是否强制要求主脑返回模块任务包（默认 `true`）
- `WHERECODE_DECOMPOSE_REQUIRE_CONFIRMATION`：`decompose-bootstrap` 后是否必须人工确认再进入 bootstrap（默认 `true`）
- `WHERECODE_DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK`：当主脑分解返回非 success 时，是否允许使用 `requirements/module_hints` 生成合成分解回退（默认 `true`）
- `WHERECODE_COMMAND_ORCHESTRATE_POLICY_ENABLED`：是否启用 command 前缀触发 orchestrate 策略（默认 `true`）
- `WHERECODE_COMMAND_ORCHESTRATE_PREFIXES`：命令编排前缀列表（默认 `/orchestrate,orchestrate:,编排:,主流程:`）
- `WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_MAX_MODULES`：命令编排默认模块上限（默认 `6`，范围 `1..20`）
- `WHERECODE_COMMAND_ORCHESTRATE_DEFAULT_STRATEGY`：命令编排默认策略（默认 `balanced`，可选 `speed|balanced|safe`）

## 智能体路由规则

- 规则文件默认位于 `control_center/agents.routing.json`
- 每条规则支持：
  - `id`：规则唯一标识（建议显式设置，便于观测）
  - `agent`：目标智能体
  - `keywords`：关键词数组（命中即路由）
  - `priority`：优先级（数字越小优先）
  - `enabled`：是否启用

## 开发约定

- 先保证最小可运行，再逐步扩展模块。
- 所有协议结构优先在 `models/` 统一定义。
- 面向 Phase 2+ 的扩展点优先放在 `../action_layer/` 和 `services/`。
- 单元测试依赖 `httpx`（FastAPI TestClient），已包含在 `requirements.txt`。
- 状态与错误契约以 `../docs/protocol.md` 为准（含状态机与 404/409/422 约束）。
- OpenAPI 变更后需运行 `python ../scripts/update_openapi_snapshot.py` 并回归测试。
