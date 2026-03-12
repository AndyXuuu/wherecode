# WhereCode: 跨时空 AI 协作指挥中心

> Fuel the Machine：本项目 100% 由 AI 编写。若你希望支持高质量输出与 MCP 边界探索，可赞助 Tokens 或 API Credits。
> 赞助 / 联系：[andy1770@proton.me](mailto:andy1770@proton.me)

WhereCode 是一套创新的个人开发工作流架构。它将开发者从书房显示器前解放出来，利用手机作为意图终端，让 PC 成为执行中枢，并与多位 AI 合作伙伴深度协同。

[English](./README.md) | [简体中文](./README.zh-CN.md)

## V2 快照

## AI 交付边界

- AI 负责端到端交付。
- 用户只提供目标和建议。

## V2 定位

V2 对标 OpenClaw / OpenCode / Oh My OpenCode 的使用方式：
- 单命令启动
- plan/build 双模式
- 自动执行闭环与结构化产物
- 里程碑节点进行人工检查

## 架构

1. `command_center/`
- 输入与可视化。

2. `control_center/`
- 主脑：需求拆解、调度、门禁、恢复、状态持久化。

3. `action_layer/`
- 执行层 provider/runtime。

4. `project/<key>/`
- 可重建子项目工作区。
- 需求文件是唯一事实来源。

详细文档：
- `docs/ARCHITECTURE_V2.md`
- `docs/OPERATIONS_V2.md`
- `docs/V2_PROJECT_PLAN.md`
- `docs/V2_PROJECT_PLAN.zh-CN.md`

## 核心命令

```bash
# 主项目编排路径
bash scripts/stationctl.sh main-orchestrate
bash scripts/stationctl.sh plan-autopilot
bash scripts/stationctl.sh plan-autopilot --max-tasks 3
bash scripts/check_all.sh main

# V2 需求驱动路径
bash scripts/stationctl.sh v2-run stock-sentiment
bash scripts/stationctl.sh v2-run stock-sentiment --mode plan
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode test
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode dev --reset-dev-state true
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode dev
bash scripts/check_all.sh v2

# 统一检查 API（远端看进度）
bash scripts/check_all.sh v2 --async
curl "http://127.0.0.1:8000/ops/checks/latest?scope=v2" -H "X-WhereCode-Token: change-me"
```

Codex App 斜杠入口：

```text
/plan-autopilot
/plan-autopilot-strict
```

## 需求输入

- Canonical：`project/requirements/stock-sentiment.md`
- 运行快照：`project/stock-sentiment/REQUIREMENTS.md`

## 可复用能力封装

- Registry：`control_center/capabilities/registry.json`
- 契约 Schema：`control_center/capabilities/capability_contract.schema.json`
- 开发路由矩阵：`control_center/capabilities/dev_routing_matrix.json`
- 模板：`control_center/capabilities/templates/*.manifest.json`
- 本地校验：
  - `python3 scripts/capability_contract_check.py`
  - `python3 scripts/capability_contract_check.py --manifest control_center/capabilities/templates/agent.manifest.json`
  - `python3 scripts/dev_routing_matrix_check.py`

## 开源协议

本项目采用 GNU Affero General Public License v3.0 (AGPL-3.0)。
详见 `LICENSE`。
