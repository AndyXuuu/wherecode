# v3 Task Board (Main Business) / v3 任务看板（主业务）

Updated: 2026-03-06

## 1) Status / 状态

- `todo`
- `doing`
- `blocked`
- `done`

## 2) Validation Scope / 校验范围

- `quick`: daily development loop / 日常开发循环。
- `full`: backend full regression / 后端完整回归。
- `release`: release gate (`full + frontend + optional project checks`) / 发布门禁（`full + frontend + 可选 project 检查`）。

## 3) Active Sprint: GO4 / 当前冲刺：GO4

| ID | Task / 任务 | Owner / 负责人 | Depends / 依赖 | Status / 状态 | Check Scope / 校验范围 | Trigger / 触发条件 |
| --- | --- | --- | --- | --- | --- | --- |
| GO4-T1 | remediate provider/network access on target host / 修复目标主机 provider/网络访问 | ops | GO3 | done | release | `GO3=done` |
| GO4-T2 | rerun provider check + recovery drill until pass / 重跑 provider 检查 + recovery drill 直至通过 | qa-test | GO4-T1 | done | release | `GO4-T1=done` |

## 4) Release Track / 发布轨道

| Milestone / 里程碑 | Gate / 门禁 | Status / 状态 | Check Scope / 校验范围 | Trigger / 触发条件 |
| --- | --- | --- | --- | --- |
| MB1 | orchestration API closed loop / 编排 API 闭环 | done | full | baseline features complete / 基线能力完成 |
| MB2 | command-trigger orchestration / 指令触发编排 | done | full | `MB1=done` |
| MB3 | real project dry-run / 真实项目演练 | done | full | `MB2=done` |
| MB4 | release readiness package / 发布就绪包 | done | release | `MB3=done` |
| MB5 | go-live decision checkpoint / 上线决策检查点 | done | release | `MB4=done` |
| REL1 | release notes + signoff package / 发布说明与签发包 | done | release | `MB5=done` |
| GO1 | launch rehearsal + sanity / 上线演练与稳定性确认 | done | release | `REL1=done` |
| GO2 | stability observation / 稳定性观察 | done | release | `GO1=done` |
| GO3 | target-host go-live validation / 目标主机上线验证 | done | release | `GO2=done` |
| GO4 | provider/recovery remediation / provider/recovery 修复 | done | release | `GO3=done` |

## 5) Validation Cadence / 校验节奏

- Daily development loop / 日常开发循环:
  - `bash scripts/check_all.sh quick`
  - `bash scripts/stationctl.sh check quick`
- Milestone / release gates / 里程碑与发布门禁:
  - `bash scripts/check_backend.sh full`
  - `bash scripts/check_all.sh release`
  - `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`

## 6) Next Action / 下一步

- Keep GO4 validation bundle in periodic checks (`go4_provider_probe` + `action_layer_llm_check` + `action_layer_llm_smoke` + `v3_recovery_drill`) / 将 GO4 验证包纳入周期性检查（`go4_provider_probe` + `action_layer_llm_check` + `action_layer_llm_smoke` + `v3_recovery_drill`）。
