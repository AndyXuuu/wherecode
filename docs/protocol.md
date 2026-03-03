# WhereCode 协议说明（HTTP 异步）

> 更新（2026-03-03）：本文件描述当前 API 契约。  
> 系统/角色/状态机规范见 `docs/system_spec.md`。

本项目使用 **HTTP 异步指挥模型**，不依赖长连接。

核心原则：

- Command Center 通过 `POST` 提交命令
- Control Center 立即返回 `202 Accepted` 与 `command_id`
- 客户端通过 `GET /commands/{id}` 轮询状态
- 审批命令通过单独的 `POST /commands/{id}/approve` 触发继续执行
- 除 `/healthz` 外，接口默认要求请求头 `X-WhereCode-Token`（或 `Authorization: Bearer <token>`）

---

## 1) 资源层级

- 项目：`/projects`
- 任务：`/projects/{project_id}/tasks`
- 命令：`/tasks/{task_id}/commands`

管理主线：`项目 -> 任务 -> 命令`

---

## 2) 创建项目

### 请求
`POST /projects`

```json
{
  "name": "wherecode-mobile",
  "description": "mobile command center workstream",
  "owner": "andy",
  "tags": ["ios", "command-center"]
}
```

请求头示例：

```text
X-WhereCode-Token: change-me
```

### 响应
`201 Created`

```json
{
  "id": "proj_abc123",
  "name": "wherecode-mobile",
  "status": "active"
}
```

---

## 3) 创建任务

### 请求
`POST /projects/{project_id}/tasks`

```json
{
  "title": "login-refactor",
  "description": "refactor auth module",
  "priority": 3,
  "assignee_agent": "auto-agent"
}
```

说明：
- `assignee_agent` 为空时将使用默认值 `auto-agent`
- 所有任务默认由智能体执行
- `auto-agent` 会按路由规则自动选择执行智能体（如 `test-agent` / `review-agent` / `coding-agent`）

### 响应
`201 Created`

```json
{
  "id": "task_xyz789",
  "project_id": "proj_abc123",
  "title": "login-refactor",
  "status": "todo"
}
```

---

## 4) 提交命令（异步）

### 请求
`POST /tasks/{task_id}/commands`

```json
{
  "text": "重构登录模块并运行单元测试",
  "source": "user",
  "requested_by": "andy",
  "requires_approval": false
}
```

### 响应
`202 Accepted`

```json
{
  "command_id": "cmd_1234abcd",
  "task_id": "task_xyz789",
  "project_id": "proj_abc123",
  "status": "queued",
  "poll_url": "/commands/cmd_1234abcd"
}
```

---

## 5) 轮询命令状态

### 请求
`GET /commands/{command_id}`

### 响应（运行中）
```json
{
  "id": "cmd_1234abcd",
  "status": "running",
  "text": "重构登录模块并运行单元测试"
}
```

### 响应（成功）
```json
{
  "id": "cmd_1234abcd",
  "status": "success",
  "output_summary": "mock execution completed",
  "executor_agent": "coding",
  "trace_id": "act_01abc234def5"
}
```

### 响应（失败）
```json
{
  "id": "cmd_1234abcd",
  "status": "failed",
  "error_message": "mock execution failed by command content",
  "executor_agent": "coding",
  "trace_id": "act_99fedc22aa11"
}
```

---

## 6) 审批命令

当命令提交时 `requires_approval=true`，其状态为 `waiting_approval`。

### 请求
`POST /commands/{command_id}/approve`

```json
{
  "approved_by": "andy"
}
```

### 响应
`200 OK`

```json
{
  "id": "cmd_approve01",
  "status": "queued",
  "approved_by": "andy"
}
```

---

## 7) 聚合查询

- `GET /projects`：项目列表
- `GET /projects/{project_id}/tasks`：任务列表
- `GET /tasks/{task_id}/commands`：任务命令列表
- `GET /projects/{project_id}/snapshot`：项目下任务+命令快照
- `GET /action-layer/health`：Action Layer 健康状态（由 Control Center 代理）
- `POST /action-layer/execute`：Action Layer 执行入口（由 Control Center 代理）
- `GET /metrics/summary`：运行指标汇总（成功率、平均耗时、运行中命令等）
- `GET /agent-routing`：查看当前生效路由规则
- `PUT /agent-routing`：更新路由规则（写回配置文件）
- `POST /agent-routing/reload`：重载智能体路由规则并返回当前生效配置

---

## 8) 状态机约束（实现契约）

### 8.1 命令状态

- 非审批命令：`queued -> running -> success|failed`
- 审批命令：`waiting_approval -> (approve) -> queued -> running -> success|failed`
- 执行来源：由 Control Center 调用 Action Layer `/execute`，并把 `agent/trace_id` 回填到命令记录
- 失败判定（当前 mock 规则）：命令文本包含 `fail` 或 `error` 时进入 `failed`
- 路由元信息：
  - `metadata.routing_reason`：`explicit_assignee|keyword_rule|default_agent`
  - `metadata.routing_keyword`：仅在 `keyword_rule` 时出现
  - `metadata.routing_rule_id`：命中的路由规则 ID，仅在 `keyword_rule` 时出现

### 8.2 任务状态（按命令聚合）

同一任务下多条命令并存时，任务状态按优先级聚合：

1. 任一命令 `waiting_approval` -> 任务 `waiting_approval`
2. 任一命令 `queued|running` -> 任务 `in_progress`
3. 任一命令 `failed` -> 任务 `failed`
4. 任一命令 `success` -> 任务 `done`
5. 任一命令 `canceled` -> 任务 `canceled`
6. 无命令 -> 任务 `todo`

### 8.3 项目活跃任务计数

- `active_task_count` = 任务状态属于 `{todo, in_progress, waiting_approval}` 的数量
- 命令状态变化后必须同步刷新 `active_task_count`

### 8.4 运行指标（Metrics）

`GET /metrics/summary` 返回如下核心字段：

- `in_flight_command_count`：处于 `queued|running` 的命令数量
- `waiting_approval_count`：等待审批命令数量
- `success_rate`：`success / (success + failed)`，无终态命令时为 `0`
- `average_duration_ms`：终态命令平均执行耗时（毫秒）
- `executor_agent_counts`：按执行智能体聚合的命令数量
- `routing_reason_counts`：按路由原因聚合的命令数量
- `routing_keyword_counts`：按命中关键词聚合的次数
- `routing_rule_counts`：按命中路由规则 ID 聚合的次数
- `recent_windows`：固定窗口（5/15/60 分钟）命令量、成功率、平均耗时

---

## 9) 错误响应契约

### 9.1 404 Not Found

- `project not found`
- `task not found`
- `command not found`

### 9.2 409 Conflict

- `command does not require approval`
- `command is not waiting approval`

### 9.3 401 Unauthorized

- `unauthorized`

说明：
- 缺少 token
- token 不匹配

### 9.4 422 Validation Error

当请求体字段不合法（如 `name/title/text/approved_by` 为空）时返回 FastAPI 默认 422 结构：

- `detail` 为数组
- 每项包含 `loc` / `msg` / `type`

---

## 10) OpenAPI 契约

运行时 OpenAPI 描述地址：`GET /openapi.json`。

当前需保持稳定的核心路径：

- `/healthz`
- `/action-layer/health`
- `/action-layer/execute`
- `/projects`
- `/projects/{project_id}/tasks`
- `/tasks/{task_id}`
- `/tasks/{task_id}/commands`
- `/commands/{command_id}`
- `/commands/{command_id}/approve`
- `/projects/{project_id}/snapshot`

关键模型契约：

- `CommandAcceptedResponse` 必须包含：
  - `command_id`
  - `task_id`
  - `project_id`
  - `status`
 - `poll_url`

---

## 11) v3 Workflow（已可跑通最小闭环）

当前新增的 v3 路径：

- `POST /v3/workflows/runs`：创建 workflow run
- `POST /v3/workflows/runs/{run_id}/bootstrap`：按模块列表自动生成标准流水线
- `POST /v3/workflows/runs/{run_id}/execute`：执行 ready queue，直到阻塞或终态
- `GET /v3/workflows/runs/{run_id}`：查看 run 状态
- `GET /v3/workflows/runs/{run_id}/workitems`：查看 workitem 列表
- `GET /v3/workflows/runs/{run_id}/gates`：查看门禁执行记录
- `GET /v3/workflows/runs/{run_id}/artifacts`：查看工件记录（验收报告/发布说明/回滚预案）
- `GET /v3/workflows/workitems/{workitem_id}/discussions`：查看讨论会话
- `POST /v3/workflows/workitems/{workitem_id}/discussion/resolve`：提交决策并恢复执行
- `POST /v3/workflows/workitems/{workitem_id}/approve`：审批等待审批的 workitem

标准流水线（每模块）：

`module-dev -> doc-manager -> qa-test -> security-review`

全局收敛：

`integration-test -> acceptance -> release-manager`

讨论机制（已接入）：

- Action Layer 返回 `status="needs_discussion"` 时，workitem 进入 `needs_discussion`
- workflow run 状态进入 `blocked`
- 通过 discussion resolve 接口提交决策后，workitem 回到 `ready`，可继续执行
- 预算、超时、重复指纹循环会触发失败收敛

门禁与回流（已接入）：

- gate 角色：
  - `doc-manager` -> doc gate
  - `qa-test` / `integration-test` -> test gate
  - `security-review` -> security gate
- gate 失败时：
  - 若模块可回流且未超重试预算，自动生成该模块的新一轮 `module-dev -> doc-manager -> qa-test -> security-review`
  - 自动重连 `integration-test` 对应的模块终点依赖
  - 超过回流预算则收敛为 `failed`

发布审批与工件（已接入）：

- 当开启 `WHERECODE_RELEASE_APPROVAL_REQUIRED=true` 时，`release-manager` 阶段进入 `waiting_approval`
- 未审批不可执行，通过 approve 接口后恢复为 `ready`
- 通过后可继续 execute 到终态
- `acceptance` 阶段自动产出 `acceptance_report`
- `release-manager` 阶段自动产出 `release_note` 和 `rollback_plan`
