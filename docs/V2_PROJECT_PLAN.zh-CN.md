# WhereCode V2 项目规划

更新时间：2026-03-09

## 1. 目标

构建面向程序员的自治工程编排系统。

V2 对标基线：
- OpenClaw
- OpenCode
- Oh My OpenCode

核心目标：
- 主项目通过单命令驱动需求到执行的全流程。
- 子项目可按需求反复重建。
- 运行产物结构化、可检查、可回放。

## 2. 范围

纳入范围：
- 主项目编排流程（`plan` + `build`）。
- 需求驱动的子项目生成与执行。
- 标准化运行报告（`docs/v2_reports/latest_*.json`）。
- 命令与检查入口统一（`stationctl`、`check_all`）。
- API 驱动的统一检查入口（远端可查进度/过程/报告）。

不纳入范围（V2）：
- 多主机分布式调度。
- 云端平台化部署。
- 复杂角色权限系统。

## 3. 架构基线

- `command_center/`：输入与可视化。
- `control_center/`：拆解、调度、门禁、恢复、状态持久化。
- `action_layer/`：执行 runtime/provider 桥接。
- `project/requirements/*.md`：需求唯一事实来源。
- `project/<key>/`：可重建运行工作区。

### 3.1 可复用能力封装边界（V2-M10）

| 类型 | 负责内容 | 适用场景 | 不适用场景 |
| --- | --- | --- | --- |
| Agent | 角色行为、任务拆解、流程决策、验收策略 | 需要“判断+编排” | 纯协议桥接或静态工具 |
| MCP | 外部/本地工具协议适配（http/db/filesystem/browser） | 需要稳定工具访问和权限隔离 | 主要是提示词/流程模板 |
| Skills | 可复用工作流模板（prompt + scripts + references） | 重复性领域流程，集成成本低 | 需要长生命周期有状态编排 |

选择规则：
1. 先看是否是外部系统协议接入，是则用 MCP。
2. 先看是否是重复流程模板，是则用 Skills。
3. 先看是否是跨模块跨角色决策，是则用 Agent。

## 4. 交付阶段

### P0 - 基线重置（已完成）
- 文档收敛为核心集。
- 子项目回收到“仅需求”。
- V2 命令入口就位。

### P1 - V2 主流程（已完成）
- `scripts/v2_run.sh` 支持 `plan|build`。
- `stationctl.sh` 支持 `v2-run`。
- `check_all.sh` 支持 `v2` scope。

### P2 - 稳定性与门禁（下一阶段）
- 增加 `scripts/v2_gate.sh`（报告结构/状态门禁）。
- 增加确定性 smoke 检查（需求解析与报告字段）。
- 增加验收清单（发布前检查）。

### P3 - 操作体验（下一阶段）
- 提升运行摘要可读性（短摘要 + JSON 细节）。
- 在 V2 报告中增加失败分类与重试建议。
- 增加一键回放（固定需求快照）。

### P4 - 可复用能力平台（下一阶段）
- 建立常用能力目录（避免项目间重复开发）。
- 建立 Agent/MCP/Skills 封装契约。
- 建立第三方扩展注册流（信任等级 + 审计）。

## 5. 里程碑与退出门禁

| 里程碑 | 范围 | 退出门禁 |
| --- | --- | --- |
| V2-M6 | 规划包 | 规划文档发布并接入索引 |
| V2-M7 | 中文规划包 | 中文规划文档发布并接入索引 |
| V2-M8 | 稳定性门禁 | `stationctl check v2` + `v2_gate.sh` 通过 |
| V2-M9 | 操作就绪 | plan/build/replay 可复现且文档齐全 |
| V2-M10 | 能力复用封装 | 边界、契约、扩展流程文档化且可检查 |

## 6. 交付物

必备文档：
- `docs/V2_PROJECT_PLAN.md`
- `docs/V2_PROJECT_PLAN.zh-CN.md`
- `docs/ARCHITECTURE_V2.md`
- `docs/OPERATIONS_V2.md`
- `docs/v2_reports/latest_<subproject>_v2_run.json`
- `control_center/capabilities/registry.json`
- `control_center/capabilities/capability_contract.schema.json`

必备命令：
- `bash scripts/stationctl.sh v2-run <subproject> --mode plan`
- `bash scripts/stationctl.sh v2-run <subproject> --mode build`
- `bash scripts/stationctl.sh check v2`

## 7. 执行节奏

每个任务必须按顺序执行：
1. 更新 `PLAN.md`。
2. 实施改动。
3. 执行检查。
4. 更新文档。

周循环：
- 需求修订 -> plan run -> build run -> gate check -> 文档回写。

## 8. 下一步任务

1. 发布能力目录和 Agent/MCP/Skills 边界。
2. 定义封装契约（输入/输出/错误/权限/版本/观测）。
3. 增加扩展注册模板和信任/审计检查。

## 9. 封装契约（草案）

每个可复用能力包必须包含：
- `id`、`type`、`version`、`owner`
- `entry` 与 `runtime` 元数据
- `input_schema` 与 `output_schema`（json schema 或引用）
- `error_contract`（错误码/可重试/恢复建议）
- `permission_contract`（文件/网络/环境变量/工具范围）
- `cost_budget`（timeout/token/call 预算）
- `observability`（事件/指标/日志字段）
- `compatibility`（wherecode 最低版本、平台限制）

最小生命周期：
1. 生成 package manifest。
2. 执行契约校验。
3. 注册到 capability registry。
4. 沙箱 dry-run。
5. 写审计记录并提升为 active。
