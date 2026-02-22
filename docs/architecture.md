# WhereCode 架构说明（草案）

## 三层协同

1. Command Center（Mobile）：提交意图与审批结果  
2. Control Center（Local PC）：解析意图、调度执行、输出卡片  
3. Action Layer（Agents）：执行编码/测试/诊断动作  

## 模块边界

- `control_center/api`: 对外入口（HTTP 异步接口）
- `control_center/services`: 任务编排、会话处理、通知分发
- `control_center/models`: 协议模型和领域模型
- `control_center/core`: 配置、鉴权、公共能力
- `action_layer/`: 多 Agent 能力接入与抽象
- `command_center/`: 移动端界面与异步交互（HTTP 轮询）

## 通信模式（更新）

- Command Center 通过 HTTP `POST` 提交命令
- Control Center 返回 `202 Accepted` + `command_id`
- Command Center 通过 HTTP `GET` 轮询命令状态
- 无需保持常驻连接，符合异步指挥模型

## 状态存储（新增）

- 默认：`memory`（进程内存，适合本地开发）
- 可选：`sqlite`（通过 `WHERECODE_STATE_BACKEND=sqlite` 启用）
- SQLite 路径由 `WHERECODE_SQLITE_PATH` 配置

## 观测（基础版）

- Control Center 中间件会生成 `X-Request-Id`
- 访问日志包含 `request_id/method/path/status/duration_ms`

Action Layer 当前提供本地 HTTP stub 能力端口（默认 `8100`）：

- `GET /healthz`
- `GET /capabilities`
- `POST /execute`

Control Center 对上游提供统一代理入口：

- `GET /action-layer/health`
- `POST /action-layer/execute`

## 演进方向

- Phase 1：先打通消息闭环
- Phase 2：引入多 Agent 路由
- Phase 3：接入自动化测试门禁
- Phase 4：增强观测与异步推送
