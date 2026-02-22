# Action Layer 说明

本目录承载 AI Agent 能力层，负责执行具体任务（编码、测试、诊断、摘要）。

## 目录角色

- 抽象 Agent 接口（统一 execute/health_check/capability）
- 管理多 Agent 实现（如 coding/test/review agent）
- 输出可回放的结构化执行结果给 Control Center

## 设计原则

- 所有 Agent 必须遵循统一输入输出模型。
- 失败必须返回可诊断上下文，不允许静默失败。
- 执行过程可流式回传进度，便于移动端卡片展示。

## 本地运行（当前 stub）

```bash
bash action_layer/run.sh
```

默认地址：`http://127.0.0.1:8100`

可用检查接口：

- `GET /healthz`
- `GET /capabilities`
- `POST /execute`（mock 执行，返回 success/failed + trace_id）

可选环境变量（放在 `action_layer/.env`）：

- `ACTION_LAYER_HOST`（默认 `127.0.0.1`）
- `ACTION_LAYER_PORT`（默认 `8100`）
