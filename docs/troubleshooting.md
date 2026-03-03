# WhereCode 故障排查手册

## 1) `401 unauthorized`

现象：
- 调用 `/projects`、`/tasks/*`、`/commands/*` 返回 401

排查：
1. 检查 Control Center 的 token 配置：`WHERECODE_TOKEN`
2. 检查请求头是否携带：
   - `X-WhereCode-Token: <token>` 或
   - `Authorization: Bearer <token>`
3. 前端检查：`command_center/.env` 中 `NEXT_PUBLIC_WHERECODE_TOKEN`

## 2) `502` / 无法连通 Control Center

现象：
- 前端探针显示 Control Center unreachable
- `scripts/http_async_smoke.sh` 连接失败

排查：
1. 确认服务是否启动：`bash scripts/stationctl.sh status all`
2. 检查端口占用：默认 Control 为 `8000`，Action 为 `8100`
3. 查看日志：`.wherecode/run/control-center.log`
4. 改端口后同步更新：
   - `control_center/.env` (`WHERECODE_PORT`)
   - `command_center/.env` (`NEXT_PUBLIC_CONTROL_CENTER_URL`)

## 3) Python 环境冲突

现象：
- `pip install requirements.txt` 报错
- `pytest` 命令找不到

排查：
1. 使用子项目虚拟环境：
   - `python3 -m venv control_center/.venv`
   - `control_center/.venv/bin/pip install -r control_center/requirements.txt`
2. 运行测试时显式指定：
   - `control_center/.venv/bin/pytest -q`
3. 不在根目录维护全局 Python 依赖文件

## 4) 前端构建失败（Next/pnpm）

现象：
- `Cannot find module ...` 或 `next build` 报错

排查：
1. 重新安装依赖：`pnpm --dir command_center install`
2. 清理构建产物：删除 `command_center/.next`
3. 重新构建：`pnpm --dir command_center build`

## 5) Action Layer 无响应

现象：
- `GET /action-layer/health` 返回 503

排查：
1. 确认 Action Layer 已启动：`bash scripts/stationctl.sh status action-layer`
2. 检查 Action 日志：`.wherecode/run/action-layer.log`
3. 检查 Control Center 配置：
   - `ACTION_LAYER_BASE_URL=http://127.0.0.1:8100`

## 6) 快速回归命令

```bash
bash scripts/check_all.sh
bash scripts/full_stack_smoke.sh
bash scripts/v3_workflow_smoke.sh
```

## 7) v3 run 卡在 `blocked`

现象：
- `POST /v3/workflows/runs/{run_id}/execute` 返回 `run_status=blocked`
- 响应里有 `waiting_discussion_workitem_ids`

排查：
1. 拉取 discussion：
   - `GET /v3/workflows/workitems/{workitem_id}/discussions`
2. 提交决策：
   - `POST /v3/workflows/workitems/{workitem_id}/discussion/resolve`
3. 再次执行：
   - `POST /v3/workflows/runs/{run_id}/execute`

## 8) v3 run 卡在 `waiting_approval`

现象：
- `run_status=waiting_approval`
- 响应里有 `waiting_approval_workitem_ids`

排查：
1. 检查是否开启 release 审批开关：
   - `WHERECODE_RELEASE_APPROVAL_REQUIRED=true`
2. 对目标 workitem 执行审批：
   - `POST /v3/workflows/workitems/{workitem_id}/approve`
3. 再次执行 run：
   - `POST /v3/workflows/runs/{run_id}/execute`

## 9) v3 run 频繁 `failed`（模块回流耗尽）

现象：
- 同模块 gate 连续失败后 run 终态 `failed`
- workitem metadata 可能含 `reflow_error=reflow_budget_exhausted`

排查：
1. 查看 gate 记录：
   - `GET /v3/workflows/runs/{run_id}/gates`
2. 检查模块标记是否触发失败规则（如 `doc-fail` / `test-fail` / `security-fail`）
3. 调高回流预算（如需要）：
   - `WHERECODE_MAX_MODULE_REFLOWS=2`

## 10) Control Center 重启后 v3 运行记录丢失

现象：
- 重启后 `GET /v3/workflows/runs/{run_id}` 返回 404
- gates/artifacts/discussions 查询为空

排查：
1. 检查是否启用 SQLite 持久化：
   - `WHERECODE_STATE_BACKEND=sqlite`
   - `WHERECODE_SQLITE_PATH` 指向可写路径
2. 检查 SQLite 文件是否存在并持续增长（如 `.wherecode/state.db`）
3. 确认重启前后环境变量一致，避免一次 `memory` 一次 `sqlite`
4. 若文件损坏或误删，恢复最近备份后重启服务，再次执行 `scripts/v3_workflow_smoke.sh` 验证恢复链路
