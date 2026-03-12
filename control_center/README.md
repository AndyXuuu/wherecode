# Control Center 说明

本目录是 WhereCode 的执行中枢（Control Center），负责 API、会话、路由和任务编排。
通信模式为 HTTP 异步：提交命令后返回 `202`，客户端通过轮询获取执行状态。
同时对 Action Layer 提供统一代理接口：

- `GET /action-layer/health`
- `POST /action-layer/execute`
- `GET /agent-rules`（查看 main/subproject 角色规则注册表）
- `POST /agent-rules/reload`（热重载角色规则注册表）
- `PUT /context/memory/items`（写入/更新 context memory item）
- `GET /context/memory/items`（按 scope + key 查询 item）
- `DELETE /context/memory/items`（删除 item，落 tombstone）
- `GET /context/memory/namespaces/{scope}/items`（按命名空间列出 items）
- `GET /context/memory/resolve`（按 shared/project/run 分层解析上下文）
- `GET /metrics/summary`（运行指标聚合）
- `GET /agent-routing`（查看当前路由规则）
- `PUT /agent-routing`（更新路由规则）
- `POST /agent-routing/reload`（热重载路由规则）

V3 workflow decomposition confirmation flow:

- `POST /v3/workflows/runs/{run_id}/decompose-bootstrap`
- `GET /v3/workflows/runs/{run_id}/decompose-bootstrap/pending`
- `GET /v3/workflows/runs/{run_id}/decompose-bootstrap/status`
- `GET /v3/workflows/runs/{run_id}/routing-decisions`
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
- command 编排澄清门控：需求文本包含 `tbd/todo/待定/???` 等歧义标记时会先阻断并要求澄清；确认后可追加 `--clarified=true` 重试。

## 目录结构

- `main.py`: FastAPI 应用入口（当前提供 `/healthz`）
- `requirements.txt`: Control Center Python 依赖
- `.env.example`: Control Center 环境变量示例
- `run.sh`: Control Center 本地启动脚本
- `api/`: HTTP 异步接口层
  - `api/action_layer_routes.py`: action-layer 代理 routes（`/action-layer/*`）
  - `api/agent_rules_routes.py`: agent 角色规则注册表 routes（`/agent-rules*`）
  - `api/agent_routing_routes.py`: agent 路由配置 routes（`/agent-routing*`）
  - `api/context_memory_routes.py`: context/memory namespace routes（`/context/memory/*`）
  - `api/hierarchy_routes.py`: 主流程层级 routes（projects/tasks/commands/snapshot）
  - `api/metrics_routes.py`: 指标与指标策略 routes（`/metrics/*`）
  - `api/ops_check_routes.py`: ops check routes（`/ops/checks/*`）；统一转发到 runtime 服务
  - `api/workflow_core_routes.py`: workflow core routes (`/v3/workflows/runs*`, `/workitems*`)；通过 runtime provider 读取当前 scheduler/engine，避免闭包固定旧实例
  - `api/workflow_execution_routes.py`: workflow execute/discussion routes（`/v3/workflows/runs/{run_id}/execute` + discussion APIs）
  - `api/workflow_orchestration_routes.py`: workflow 编排 routes（decompose/orchestrate/recover）
- `core/`: 配置、鉴权、通用基础能力
- `models/`: Pydantic 数据模型（已包含项目->任务->命令层级结构）
- `services/`: 业务服务层（会话、任务、通知）
  - `services/app_wiring.py`: app 中间件/路由挂载与 ops-check runtime 装配
  - `services/config_bootstrap.py`: 控制中心环境变量解析与配置归一化
  - `services/context_memory_store.py`: context/memory 命名空间存储与分层解析（shared/project/run）
  - `services/agent_rules_registry.py`: agent 角色规则注册表加载/校验/导出（main/subproject）
  - `services/ops_check_runtime.py`: ops check run 生命周期、状态持久化、日志与报告落盘
  - `services/dev_routing_matrix.py`: 开发专精路由矩阵加载/匹配/任务包注入
  - `services/workflow_execution_runtime.py`: workflow execute 生命周期（auto-advance + execute 结果融合）
  - `services/workflow_decompose_helpers.py`: chief decompose prompt 构造与 helper 委托
  - `services/workflow_decompose_helpers_coverage.py`: decompose coverage/mapping/fallback 辅助逻辑
  - `services/workflow_decompose_helpers_tasks.py`: module task package 提取/校验/默认值辅助逻辑
  - `services/workflow_decompose_preview_support.py`: decompose preview/cache 辅助逻辑
  - `services/workflow_decompose_runtime.py`: decompose bootstrap + pending/status/preview/advance/confirm 生命周期
  - `services/workflow_decompose_runtime_helpers.py`: decompose runtime 辅助逻辑（chief 结果校验、pending 视图提取、task package 归一化）
  - `services/workflow_decompose_runtime_policy.py`: decompose runtime 策略辅助逻辑（chief 请求/记录、confirmation metadata、advance-loop 汇总）
  - `services/workflow_decompose_runtime_advance.py`: decompose advance 动作分发辅助逻辑（preview/confirm/bootstrap/execute/tick）
  - `services/workflow_decompose_support.py`: decompose aggregate status / routing decisions 辅助逻辑
  - `services/workflow_api_handlers.py`: API handler 适配层（decompose/orchestrate/execute 透传调度）
  - `services/runtime_bootstrap.py`: runtime/service 组装（scheduler/engine/dispatch/api-handlers）与 provider 绑定
  - `services/workflow_orchestration_runtime.py`: workflow orchestrate/recover 生命周期
  - `services/workflow_orchestration_runtime_policy.py`: orchestrate 策略执行参数与 recovery 请求/响应策略辅助逻辑
  - `services/workflow_orchestration_support.py`: orchestrate decision/telemetry/latest-record 计算与持久化辅助逻辑
  - `services/workflow_orchestration_support_decision.py`: orchestrate recovery 评分与 decision report 组装辅助逻辑
  - `services/workflow_orchestration_support_summary.py`: decompose summary、telemetry snapshot、recovery action 解析辅助逻辑
  - `services/workflow_scheduler_indexes.py`: scheduler 索引重建辅助逻辑（run/workitem/discussion/gate/artifact）
  - `services/workflow_scheduler_dependencies.py`: scheduler 依赖校验与 pending-ready 选择辅助逻辑
  - `services/workflow_scheduler_status.py`: scheduler run 状态推导与 metrics 聚合辅助逻辑
  - `services/workflow_engine_bootstrap_helpers.py`: workflow engine bootstrap 辅助逻辑（模块/任务包归一化、metadata、terminal 推导）
  - `services/workflow_engine_runtime_helpers.py`: workflow engine runtime 辅助逻辑（执行文本、结果汇总、reflow 图搜索、默认 artifact 产出）
  - `services/metrics_authorization.py`: metrics policy/rollback 鉴权辅助逻辑
  - `services/metrics_alert_policy_store_rollback.py`: rollback approval/purge audit 的持久化与时序过滤辅助逻辑
  - `services/metrics_alert_policy_store_policy.py`: metrics alert policy 的归一化/查询/统计与 purge 计算辅助逻辑
  - `services/metrics_alert_policy_store_io.py`: metrics alert policy/verify registry/audit 的文件 I/O 辅助逻辑
  - `services/metrics_alert_policy_store_verify.py`: verify policy registry 的 normalize/serialize 辅助逻辑
  - `services/command_orchestration_policy.py`: command `/orchestrate` 策略解析与执行状态回写
  - `services/command_dispatch.py`: command 分发执行适配（策略短路 + 路由元数据 + action 调用）
- `../action_layer/`: Agent 抽象与实现（Action Layer）

## 环境变量

- `WHERECODE_AUTH_ENABLED`：是否开启鉴权，默认 `true`
- `WHERECODE_TOKEN`：Control Center API token，默认 `change-me`
- `WHERECODE_ALLOWED_ORIGINS`：CORS 白名单，默认 `http://localhost:3000`
- `ACTION_LAYER_BASE_URL`：Action Layer 代理地址，默认 `http://127.0.0.1:8100`
- `ACTION_LAYER_TIMEOUT_SECONDS`：Action Layer 调用超时秒数，默认 `180`
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
- `WHERECODE_COMMAND_ORCHESTRATE_RESTART_CANCELED_POLICY`：取消态 run 自动重启策略（默认 `off`，可选 `off|auto_if_no_requirements|always`）
- `WHERECODE_DEV_ROUTING_MATRIX_FILE`：开发专精路由矩阵文件（默认 `control_center/capabilities/dev_routing_matrix.json`）
- `WHERECODE_AGENT_RULES_REGISTRY_FILE`：agent 角色规则注册表文件（默认 `control_center/capabilities/agent_rules_registry.json`）

运行时配置查询：
- `GET /config/command-orchestrate-policy`：返回 command orchestrate 策略有效值（含 `restart_canceled_policy`）。

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
