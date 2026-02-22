# Scripts 说明

本目录放置项目脚本工具，例如：

- 本地开发辅助脚本
- CI 前置检查脚本
- 日志清理与数据迁移脚本
- 子项目统一命令入口（`stationctl.sh`，支持 install/dev/start/stop/status/check）
- HTTP 异步链路 smoke 脚本（`http_async_smoke.sh`）
- Action Layer smoke 脚本（`action_layer_smoke.sh`）
- 本地统一校验脚本（`check_all.sh`，后端测试 + 前端构建）

约定：
- 脚本默认可重复执行（幂等）。
- 关键脚本需在文件头说明用途和输入参数。
- `http_async_smoke.sh` 默认读取 `WHERECODE_TOKEN`（未设置时使用 `change-me`）。
