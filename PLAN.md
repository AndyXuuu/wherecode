# WhereCode 工程规划（v2）

更新日期：2026-02-22

## 1. 项目定位

WhereCode 的目标保持不变：以 **Command Center（移动端）** 下达意图、以 **Control Center（本地编排）** 执行调度、以 **Action Layer（Agent 执行层）** 落地动作，形成可异步指挥、可追踪、可持续扩展的工程体系。

---

## 2. 当前进度盘点（全面检查结论）

### 2.1 已完成能力

- 三子项目结构稳定：`command_center/`、`control_center/`、`action_layer/`，依赖隔离已落地。
- HTTP 异步主链路完成：`POST /tasks/{id}/commands` + `GET /commands/{id}` + `POST /commands/{id}/approve`。
- 管理维度落地：`项目 -> 任务 -> 命令` 数据模型和 API 已贯通。
- Pencil 对齐完成：4 个主页面 + 3 个子页面已按画板映射实现。
- 主题体系完成：岩板灰主色 + dark/light 模式切换，Next + Tailwind 已统一。
- Action Layer 已具备本地 HTTP stub：`/healthz`、`/capabilities`、`/execute`。
- Control Center 已提供 Action Layer 代理：`/action-layer/health`、`/action-layer/execute`。
- 工程化脚本成型：`stationctl.sh`（install/dev/start/stop/status/check）+ smoke + check。
- CI 已落地：后端 `pytest -q`、前端 `pnpm build`。
- 测试与契约：OpenAPI 快照、协议与状态机测试齐备（当前 34 项通过）。

### 2.2 尚未完成/待强化

- 鉴权尚未真正启用（`WHERECODE_TOKEN` 已定义但未在请求链路强制校验）。
- 命令执行仍为 mock 逻辑主导，未将主命令生命周期与 Action Layer 真执行结果完全绑定。
- 存储仍为内存态，进程重启后状态丢失（缺少 SQLite/Redis 持久层）。
- 缺少结构化审计日志与核心指标（耗时、失败率、重试次数）。
- 集成测试仍偏单体进程，缺少“多进程真实联调”自动化回归。

---

## 3. 里程碑状态

- M1 工程地基：已完成
- M2 HTTP 异步 MVP：已完成
- M3 Agent 编排（初版代理）：部分完成
- M4 质量闭环（契约 + CI）：部分完成
- M5 运维可观测性：未完成

---

## 4. 新阶段计划（接下来 3 周）

## Phase A（2026-02-23 ~ 2026-03-01）：执行链路实化

目标：把“命令状态机”与 Action Layer 真执行结果打通。

交付：
- 将命令执行结果统一来自 Action Layer（成功/失败/摘要/trace_id）。
- 命令记录补充执行轨迹字段（如 `trace_id`、`agent`、`executor_status`）。
- 新增命令执行失败重试策略（最小 1 次，明确可配置）。
- 为执行链路补充契约测试与异常测试。

验收：
- 命令终态与 Action Layer 返回一致。
- 失败时可追踪 trace_id，且前端可见。

## Phase B（2026-03-02 ~ 2026-03-08）：安全与持久化

目标：从演示级系统升级为可持续运行系统。

交付：
- 实现 Token 鉴权中间件（可按路径白名单放行 `healthz`）。
- 引入 SQLite 持久化（项目/任务/命令）并保留 in-memory 开发模式。
- 增加迁移脚本和数据导出脚本。
- 回归测试覆盖“重启后数据不丢失”。

验收：
- 未携带/错误 Token 的受保护接口返回 401。
- 服务重启后可查询到历史项目与命令。

## Phase C（2026-03-09 ~ 2026-03-15）：观测与运维体验

目标：构建可诊断、可运营的日常开发体验。

交付：
- 结构化日志（request_id/project_id/task_id/command_id/trace_id）。
- 指标端点（成功率、平均耗时、运行中命令数）。
- `stationctl` 增加日志查看辅助（tail 最近日志）。
- 增加真实联调集成脚本（启动三层 -> 执行 smoke -> 清理）。

验收：
- 任意失败命令可在日志中一键追溯完整链路。
- 联调回归脚本可稳定复现核心链路。

---

## 5. 本周执行清单（优先级）

P0：
1. Control Center 命令执行改为调用 Action Layer `/execute`。
2. 新增执行结果字段并同步前端 `command-lab` 展示。
3. 补充 `test_action_execution_contract` 与错误分支测试。

P1：
1. 启用 Token 鉴权（先后端，后前端请求头）。
2. 设计 SQLite 持久层接口（Repository 抽象 + in-memory 适配器）。

P2：
1. 增加日志规范与 trace 贯穿。
2. 优化 runbook 的“故障排查”分支。

---

## 6. 风险与应对

- Action Layer 接口变更风险：通过 OpenAPI 快照和契约测试锁定字段。
- 引入持久层后的复杂度上升：先抽象 Repository，再逐步替换存储实现。
- 鉴权落地影响联调效率：保留本地开发开关和 health 白名单。

---

## 7. 即刻行动（今天）

1. 完成命令执行与 Action Layer 对接方案设计（字段、状态、异常映射）。
2. 先实现最小可用版本（成功/失败映射 + trace_id 回写）。
3. 同步更新 `docs/protocol.md` 与 OpenAPI 快照并跑全量回归。
