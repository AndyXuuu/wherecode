# Tests (V3)

测试目录按层次拆分，当前仅保留 V3 主流程相关测试。

- `unit/`: 模型、服务、API 契约与门禁行为
- `integration/`: 预留
- `snapshots/`: OpenAPI 快照

建议：
- 提交前至少执行 `bash scripts/check_backend.sh quick`
- API 契约变化后执行 `python3 scripts/update_openapi_snapshot.py`
