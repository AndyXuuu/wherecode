# WhereCode 协议说明（HTTP 异步）

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
  "assignee_agent": "coding-agent"
}
```

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

---

## 8) 状态机约束（实现契约）

### 8.1 命令状态

- 非审批命令：`queued -> running -> success|failed`
- 审批命令：`waiting_approval -> (approve) -> queued -> running -> success|failed`
- 执行来源：由 Control Center 调用 Action Layer `/execute`，并把 `agent/trace_id` 回填到命令记录
- 失败判定（当前 mock 规则）：命令文本包含 `fail` 或 `error` 时进入 `failed`

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
