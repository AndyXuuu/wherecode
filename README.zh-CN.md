# WhereCode: AI 工程控制平面 (V3)

> Fuel the Machine：本项目 100% 由 AI 编写。若你希望支持高质量输出与 MCP 边界探索，可赞助 Tokens 或 API Credits。
> 赞助 / 联系：[andy1770@proton.me](mailto:andy1770@proton.me)

WhereCode 是一个面向自动化软件交付的控制平面。
它负责需求分析、阶段门禁、角色路由、证据与报告；
代码生成与改动执行交给外部执行引擎（OpenCode / OhMyOpenCode）。

[English](./README.md) | [简体中文](./README.zh-CN.md)

## V3 快照

- 单适配器执行平面：`opencode`，双策略路由（`native|ohmy`）。
- `stationctl` 已硬切 V3 主命令面（移除 `v2-*` / `subproject-*` 执行入口）。
- workflow runtime 已接入澄清门禁 + SDD 门禁 + 验收门禁：
  - `requirement_status`
  - `clarification_rounds`
  - `assumption_used`
- 远程可视化只读接口：
  - `GET /v3/runs/{id}/timeline`
  - `GET /v3/runs/{id}/artifacts`
  - `GET /v3/runs/{id}/report`

## AI 交付边界

- AI 负责端到端交付。
- 用户只提供目标和建议。

## 项目定位

- 主项目负责编排与验收门禁。
- 外部执行器负责“干活”（代码生成/修改）。
- 用户只提供目标和建议，AI 端到端执行。

## 架构

1. `command_center/`
- 输入与可视化。

2. `control_center/`
- 主脑：需求拆解、调度、门禁、恢复、状态持久化。

3. `action_layer/`
- 薄执行网关（请求归一与转发）。

4. `project/<key>/`
- 可重建子项目工作区。
- 需求文件是唯一事实来源。

5. `external/executors/`
- OpenCode / OhMyOpenCode 的本地源码工作区（用于上游更新）。
- 与主工程代码隔离，避免污染控制平面。

6. `.agents/`
- 角色规则、复用技能、路由/上下文策略、MCP 配置。
- 角色规则规范路径：`.agents/roles/<role>/AGENTS.md`。

详细文档：
- `docs/V3_PROJECT_PLAN.md`
- `docs/V3_ENGINEERING_LAYOUT.md`
- `docs/STANDARD_AGENT_REACT.md`

## 核心命令

```bash
# 主项目编排路径
bash scripts/stationctl.sh main-orchestrate
bash scripts/stationctl.sh plan-autopilot
bash scripts/stationctl.sh plan-autopilot --max-tasks 3
bash scripts/check_all.sh main
```

Codex App 斜杠入口：

```text
/plan-autopilot
/plan-autopilot-strict
```

## 需求输入

- Canonical：`project/requirements/stock-sentiment.md`

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
