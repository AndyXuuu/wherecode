# Control Center 说明

本目录是 WhereCode 的执行中枢（Control Center），负责 API、会话、路由和任务编排。
通信模式为 HTTP 异步：提交命令后返回 `202`，客户端通过轮询获取执行状态。
同时对 Action Layer 提供统一代理接口：

- `GET /action-layer/health`
- `POST /action-layer/execute`

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

- `WHERECODE_ALLOWED_ORIGINS`：CORS 白名单，默认 `http://localhost:3000`
- `ACTION_LAYER_BASE_URL`：Action Layer 代理地址，默认 `http://127.0.0.1:8100`

## 开发约定

- 先保证最小可运行，再逐步扩展模块。
- 所有协议结构优先在 `models/` 统一定义。
- 面向 Phase 2+ 的扩展点优先放在 `../action_layer/` 和 `services/`。
- 单元测试依赖 `httpx`（FastAPI TestClient），已包含在 `requirements.txt`。
- 状态与错误契约以 `../docs/protocol.md` 为准（含状态机与 404/409/422 约束）。
- OpenAPI 变更后需运行 `python ../scripts/update_openapi_snapshot.py` 并回归测试。
