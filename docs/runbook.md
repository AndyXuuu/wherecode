# WhereCode 运行手册（草案）

## 1. 统一命令入口（推荐）

在根目录使用 `stationctl` 统一管理三个子项目，不在根目录安装依赖。

```bash
# 1) 安装子项目依赖（按各自技术栈隔离）
bash scripts/stationctl.sh install all

# 2) 启动 Command Center + Control Center + Action Layer
bash scripts/stationctl.sh dev all
```

命令矩阵：

- `bash scripts/stationctl.sh install command-center`
- `bash scripts/stationctl.sh install control-center`
- `bash scripts/stationctl.sh install action-layer`
- `bash scripts/stationctl.sh dev command-center`
- `bash scripts/stationctl.sh dev control-center`
- `bash scripts/stationctl.sh dev action-layer`
- `bash scripts/stationctl.sh start all`（后台启动）
- `bash scripts/stationctl.sh status all`（查看运行状态）
- `bash scripts/stationctl.sh stop all`（后台停机）
- `bash scripts/stationctl.sh check`（后端测试 + 前端构建）

## 2. 本地启动（手动方式）

```bash
python3 -m venv control_center/.venv
source control_center/.venv/bin/activate
pip install -r control_center/requirements.txt
cp control_center/.env.example control_center/.env
bash control_center/run.sh
```

默认地址：`http://127.0.0.1:8000`

鉴权默认开启，建议先导出 token：

```bash
export WHERECODE_TOKEN=change-me
```

如需启用 SQLite 持久化：

```bash
export WHERECODE_STATE_BACKEND=sqlite
export WHERECODE_SQLITE_PATH=.wherecode/state.db
```

## 3. 快速检查

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/action-layer/health -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}"
curl http://127.0.0.1:8100/healthz
control_center/.venv/bin/pytest tests/unit/test_http_async_flow.py
control_center/.venv/bin/pytest -q
```

预期：
- `/healthz` 返回 `{"status":"ok","transport":"http-async"}`
- Action Layer `/healthz` 返回 `{"status":"ok","layer":"action","transport":"http"}`
- Control Center 响应头包含 `X-Request-Id`
- 测试通过

若修改了接口契约（路径/字段/响应模型），同步更新 OpenAPI 快照：

```bash
control_center/.venv/bin/python scripts/update_openapi_snapshot.py
control_center/.venv/bin/pytest -q
```

前端联调（Command Center）：

```bash
cd command_center
pnpm install
pnpm dev
```

打开 `http://localhost:3000/command-lab`，可直接创建项目/任务并提交命令进行轮询。  
如需查看 Pencil 页面复刻，访问 `http://localhost:3000/overview`。  
默认入口会跳转到 `http://localhost:3000/overview`。

前端构建（统一）：

```bash
cd command_center
pnpm build
```

一键校验（后端测试 + 前端构建）：

```bash
bash scripts/check_all.sh
```

后台模式日志和 PID 位于：`/Users/andyxu/Documents/project/wherecode/.wherecode/run/`

## 4. HTTP 异步指挥流程检查

推荐直接运行 smoke 脚本：

```bash
bash scripts/http_async_smoke.sh
bash scripts/action_layer_smoke.sh
```

注意：该脚本依赖 Control Center 已运行（`http://127.0.0.1:8000`）。
`action_layer_smoke.sh` 依赖 Action Layer 已运行（`http://127.0.0.1:8100`）。

或手动调用：

```bash
# 1) 创建项目
curl -sX POST http://127.0.0.1:8000/projects \
  -H "Content-Type: application/json" \
  -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  -d '{"name":"wherecode-mobile"}'

# 2) 创建任务
curl -sX POST http://127.0.0.1:8000/projects/<project_id>/tasks \
  -H "Content-Type: application/json" \
  -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  -d '{"title":"login-refactor"}'

# 3) 提交命令（返回 202 + command_id）
curl -sX POST http://127.0.0.1:8000/tasks/<task_id>/commands \
  -H "Content-Type: application/json" \
  -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  -d '{"text":"run unit tests"}'

# 4) 轮询命令状态
curl -s http://127.0.0.1:8000/commands/<command_id> \
  -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}"
```

预期：
- 命令提交接口返回 `202 Accepted`
- 命令状态按 `queued -> running -> success|failed` 变化
- 无需 WebSocket 常驻连接

## 5. 常见问题

- 端口冲突：修改 `control_center/.env` 中 `WHERECODE_PORT`
- 依赖缺失：
  - Control Center：`bash scripts/stationctl.sh install control-center`
  - Command Center：`bash scripts/stationctl.sh install command-center`
- 401 unauthorized：确认 `WHERECODE_TOKEN` 与请求头 `X-WhereCode-Token` 一致
- 环境变量未生效：确认是否已加载 `control_center/.env` 或手动导出变量
