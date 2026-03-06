# Release Map (Main Business) / 发布路线图（主业务）

Updated: 2026-03-06

## 1) Objective / 目标

- Focus on main business closure (`command -> orchestrate -> recover -> release decision`) / 聚焦主业务闭环（`command -> orchestrate -> recover -> release decision`）。
- Keep single-host reality and practical release gates / 保持单机现实约束与可执行门禁。
- Keep validation tiered (`quick` daily, `full/release` milestone) / 保持分层校验（`quick` 日常，`full/release` 里程碑）。

## 2) Milestone Map / 里程碑路线

| Milestone / 里程碑 | Target Date / 目标日期 | Scope / 范围 | Required Output / 产出 | Gate / 门禁 |
| --- | --- | --- | --- | --- |
| MB1 | 2026-03-06 | orchestration closed loop / 编排闭环 | `/orchestrate` + `/orchestrate/latest` + `/orchestrate/recover` ready / 接口可用 | API contract tests pass / API 契约测试通过 |
| MB2 | 2026-03-07 | command entry integration / 指令入口集成 | command intent can trigger orchestrate flow / 指令可触发 orchestrate 流程 | end-to-end trigger verified / 端到端触发验证 |
| MB3 | 2026-03-08 | real project dry-run / 真实项目演练 | stock-sentiment task run report / 股票舆情任务运行报告 | dry-run report generated / 演练报告产出 |
| MB4 | 2026-03-09 | release readiness / 发布就绪 | release checklist + rollback rehearsal / 发布清单 + 回滚演练 | `check_all.sh release` green / `check_all.sh release` 通过 |
| MB5 | 2026-03-10 | go-live decision / 上线决策 | acceptance package + launch recommendation / 验收包 + 上线建议 | milestone gate + acceptance ready / 里程碑门禁与验收就绪 |
| REL1 | 2026-03-10 | release signoff / 发布签发 | bilingual release notes + signoff package / 双语发布说明 + 签发包 | signoff checklist complete / 签发清单完成 |
| GO1 | 2026-03-11 | launch rehearsal / 上线演练 | launch rehearsal + post-checklist / 上线演练 + 后检查清单 | release rehearsal pass / 发布演练通过 |
| GO2 | 2026-03-12 | stability observation / 稳定性观察 | observation report + issue queue / 观察报告 + 问题队列 | observation checkpoint pass / 观察检查点通过 |
| GO3 | 2026-03-13 | target-host validation / 目标主机验证 | provider/recovery validation package / provider/recovery 验证包 | target-host validation pass / 目标主机验证通过 |
| GO4 | 2026-03-14 | provider/recovery remediation / provider/recovery 修复 | remediation report + rerun evidence / 修复报告 + 重跑证据 | provider check + recovery drill pass / provider 检查 + recovery drill 通过 |
| GO5 | 2026-03-15 | continuous ops checkpoint / 持续运营检查点 | one-command checkpoint bundle + secret gate baseline / 一键检查包 + 密钥门禁基线 | `check_all.sh ops` green / `check_all.sh ops` 通过 |

## 3) Current Position / 当前状态

- MB1: done / 已完成。
- MB2: done / 已完成。
- MB3: done (dry-run + recover + execute evidence captured) / 已完成（dry-run + recover + execute 已留证）。
- MB4: done (release baseline + evidence package + go/no-go draft ready) / 已完成（发布基线 + 证据包 + go/no-go 草案已就绪）。
- MB5: done (acceptance package + strict gate + launch recommendation ready) / 已完成（验收包 + 严格门禁 + 上线建议已就绪）。
- REL1: done (release notes + signoff package completed) / 已完成（发布说明 + 签发包已完成）。
- GO1: done (launch rehearsal + post-launch checklist completed) / 已完成（上线演练 + 上线后清单已完成）。
- GO2: done (checkpoint-01 + observation queue completed) / 已完成（检查点 01 + 问题队列已完成）。
- GO3: done (validation package produced; target-host readiness not ready due provider execution failures) / 已完成（验证包已产出；因 provider 执行失败暂不具备目标主机就绪性）。
- GO4: done (local codex-config alignment + provider execute path + recovery drill rerun passed) / 已完成（本地 codex-config 对齐 + provider 执行链路 + recovery drill 重跑通过）。
- GO5: done (one-command ops checkpoint + check entry integration completed) / 已完成（一键运营检查与统一检查入口接入完成）。

## 4) Run Commands / 执行命令

```bash
bash scripts/check_all.sh quick
bash scripts/check_backend.sh full
bash scripts/check_all.sh release
bash scripts/check_all.sh ops
bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict
bash scripts/stationctl.sh mb3-dry-run
```
