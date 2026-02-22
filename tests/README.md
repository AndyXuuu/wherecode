# Tests 说明

测试目录按层次拆分，优先保证核心链路可回归。

- `unit/`: 单元测试（模型、路由、工具函数）
- `integration/`: 集成测试（HTTP 异步协议、会话、任务流程）

建议：
- 先写协议和会话单测，再补端到端集成测试。
- 每次提交前至少跑 `pytest`。
- 当 API 契约变更时，执行 `python scripts/update_openapi_snapshot.py` 更新 OpenAPI 快照，再跑 `pytest`。
