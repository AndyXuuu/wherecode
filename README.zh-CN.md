# WhereCode

面向真实工程分工的多角色 AI 研发编排系统。

[English](./README.md) | [简体中文](./README.zh-CN.md)

## 项目一页纸（2026-03-03）

### 定位

- 主流程：`项目 -> 任务 -> 命令`（HTTP 异步）。
- 运行架构：
  - `Command Center`（UI）
  - `Control Center`（编排、策略、门禁）
  - `Action Layer`（角色 Agent）

### 已交付

- Workflow run/workitem 编排与依赖调度。
- 角色流水线：
  - `module-dev -> doc-manager -> qa-test -> security-review -> acceptance -> release-manager`
- 讨论控制（预算/超时/指纹防循环）。
- 门禁机制（doc/test/security）+ 模块 reflow。
- 指标与策略治理（审计 + 回滚审批）。
- 里程碑门禁：`scripts/v3_milestone_gate.sh`。
- SQLite 持久化与重启恢复。

### 当前阶段

- `K1-K50`：done
- `M-TEST-ENTRY`：passed
- 当前冲刺：`TST1`

### 上线门槛

- TST 矩阵全绿。
- rollback/policy 回归全绿。
- 验收与发布签字完成。
- oncall 清单完成。

## 快速开始

```bash
bash scripts/stationctl.sh install all
bash scripts/stationctl.sh dev all
bash scripts/check_all.sh
```

## 活跃文档

- 发布阶段图：`docs/release_map.md`
- 当前计划：`PLAN.md`
- 任务看板：`docs/v3_task_board.md`
- 系统规范：`docs/system_spec.md`
- API 协议：`docs/protocol.md`
- 运行手册：`docs/runbook.md`
- 值班清单：`docs/oncall_checklist.md`
- 故障排查：`docs/troubleshooting.md`

## 开源协议

AGPL-3.0，见 `LICENSE`。
