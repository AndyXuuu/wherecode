# WhereCode 单人开发清单

更新日期：2026-02-22

本清单用于把 `PLAN.md (v2)` 拆成可以直接执行的工作项。

## 已完成（里程碑）

- [x] Monorepo 三子项目结构与依赖隔离（Command/Control/Action）
- [x] Control Center HTTP 异步主流程（提交、轮询、审批、快照）
- [x] 管理维度数据结构（项目 -> 任务 -> 命令）
- [x] Pencil 画板复刻（4 主页面 + 3 子页面）
- [x] 统一视觉与主题（岩板灰主色 + dark/light）
- [x] Action Layer 本地 stub 与 Control 代理接口
- [x] 统一脚本体系（stationctl/check/smoke）
- [x] CI、OpenAPI 快照、核心单测/契约测试

## 本周（P0，必须完成）

- [ ] 命令执行生命周期绑定 Action Layer `/execute` 结果
- [ ] 命令模型补充 `trace_id` / `agent` 等执行追踪字段
- [ ] 前端 command-lab 展示 Action Layer 回执信息
- [ ] 新增执行链路契约测试（成功、失败、异常映射）
- [ ] 更新协议文档与 OpenAPI 快照

## 下周（P1，高优先）

- [ ] 启用 Token 鉴权（保留 healthz 白名单）
- [ ] 新增请求头接入说明（Command Center -> Control Center）
- [ ] 设计并接入 SQLite 持久化（可与 in-memory 切换）
- [ ] 增加“重启后数据保持”测试

## 双周后（P2，增强项）

- [ ] 结构化日志（request_id/task_id/command_id/trace_id）
- [ ] 增加运行指标（成功率、耗时、运行中命令）
- [ ] 完善联调集成脚本（启动三层 -> smoke -> 停机）
- [ ] 沉淀故障排查手册（超时、502、依赖冲突、端口占用）
