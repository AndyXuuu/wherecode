# WhereCode PLAN (Main Business) / WhereCode 计划（主业务）

Updated: 2026-03-06

## 1) Workflow DNA / 工作流基因

1. Update plan first / 先更新计划。
2. Implement changes / 再实施改动。
3. Run checks / 执行检查。
4. Write summary docs / 写总结文档。

Task log rule / 任务日志规则:
- Start: `started (doing)`.
- Finish: `completed (done)`.
- If blocked: one short blocker line.

## 2) Ownership Boundary / 责任边界

- AI executes end-to-end delivery / AI 负责端到端交付。
- User provides goals/suggestions only / 用户仅提供目标与建议。
- Main engineering files are edited directly in this repo / 主工程文件直接在本仓库修改。
- `project/` is automation-managed subproject workspace / `project/` 是自动化托管子项目工作区。
- Do not hand-edit subproject business implementation in `project/` / 不手改 `project/` 子项目业务实现。

## 3) Milestones (with expected date) / 里程碑（含预期日期）

| Milestone / 里程碑 | Target Date / 目标日期 | Scope / 范围 | Exit Gate / 退出门禁 | Status / 状态 |
| --- | --- | --- | --- | --- |
| MB1 | 2026-03-06 | chief decompose -> orchestrate -> recover API closed loop | `/orchestrate` + `/orchestrate/latest` + `/orchestrate/recover` usable | done |
| MB2 | 2026-03-07 | command entry maps to orchestrate flow by policy | one command can trigger full run orchestration | done |
| MB3 | 2026-03-08 | real project dry-run (single-host) | stock-sentiment task can be decomposed/executed/recovered end-to-end | done |
| MB4 | 2026-03-09 | local release readiness package | release checklist + runbook + rollback rehearsal green | done |
| MB5 | 2026-03-10 | go-live decision checkpoint | milestone gate + acceptance report ready for launch decision | done |
| REL1 | 2026-03-10 | release notes + signoff package | bilingual release notes + signoff package ready | done |
| GO1 | 2026-03-11 | local go-live launch prep | launch runbook rehearsal + post-checklist ready | done |
| GO2 | 2026-03-12 | local stability observation | smoke/recovery observation report ready | done |
| GO3 | 2026-03-13 | target-host go-live validation | provider/recovery validation package ready | done |
| GO4 | 2026-03-14 | provider/recovery remediation | provider execute + recovery drill pass | done |
| GO5 | 2026-03-15 | continuous ops checkpoint | secret gate + ops checkpoint bundle ready | done |

## 4) This Sprint Task Breakdown (GO5) / 本冲刺任务拆解（GO5）

| ID | Task / 任务 | Owner / 负责人 | Depends / 依赖 | Status / 状态 |
| --- | --- | --- | --- | --- |
| GO5-T1 | add one-command ops checkpoint script (secret + provider + recovery) | ops | GO4 | done |
| GO5-T2 | integrate ops checkpoint into check entry/docs | qa-test | GO5-T1 | done |

## 5) Expected Output (this week) / 本周预期产出

- By 2026-03-07: command-level orchestration trigger is runnable.
- By 2026-03-08: one real stock-sentiment project run completes full workflow loop.
- By 2026-03-09: local release checklist is green with rollback rehearsal record.
- By 2026-03-10: launch decision package is ready.

## 6) Gate Commands / 门禁命令

- Quick loop: `bash scripts/check_all.sh quick`
- Backend full: `bash scripts/check_backend.sh full`
- Release scope: `bash scripts/check_all.sh release`
- Milestone gate: `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`

## 7) Next Action / 下一步

- Close GO5-T1/T2 and publish one-command ops checkpoint.
- Keep GO4 validation bundle in routine loop: provider probe + llm check/smoke + recovery drill.
- Keep release baseline command in loop: `bash scripts/check_all.sh release`.
- Keep recovery route in loop: `/v3/workflows/runs/{run_id}/orchestrate/recover`.

## 8) Task Log (Recent) / 最近任务日志

- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-ORCHESTRATE-RECOVERY-EXECUTE-API` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-ORCHESTRATE-RECOVERY-EXECUTE-API` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MILESTONE-PLAN-RESET` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MILESTONE-PLAN-RESET` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-README-BILINGUAL-SYNC` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-README-BILINGUAL-SYNC` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-README-BILINGUAL-MIRROR-ORDER` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-README-BILINGUAL-MIRROR-ORDER` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-RELEASE-MAP-BILINGUAL-MIRROR` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-RELEASE-MAP-BILINGUAL-MIRROR` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-TASK-BOARD-BILINGUAL-MIRROR` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-TASK-BOARD-BILINGUAL-MIRROR` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-PLAN-BILINGUAL-MIRROR` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-PLAN-BILINGUAL-MIRROR` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-RUNBOOK-BILINGUAL-MIRROR` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-RUNBOOK-BILINGUAL-MIRROR` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-COMMAND-ORCHESTRATE-POLICY` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-COMMAND-ORCHESTRATE-POLICY` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-COMMAND-WORKFLOW-STATE-PERSISTENCE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-COMMAND-WORKFLOW-STATE-PERSISTENCE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB2-T3-MIN-E2E-CONTRACTS` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB2-T3-MIN-E2E-CONTRACTS` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB2-T4-RUNBOOK-API-DOC-SYNC` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB2-T4-RUNBOOK-API-DOC-SYNC` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB3-DRY-RUN-SEED-TOOLING` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB3-DRY-RUN-SEED-TOOLING` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB3-T4-RECOVERY-EXECUTE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB3-T4-RECOVERY-EXECUTE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB3-T5-UNBLOCK-FLOW` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB3-T5-UNBLOCK-FLOW` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB4-RELEASE-GATE-READINESS` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB4-RELEASE-GATE-READINESS` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB4-T2-EVIDENCE-PACKAGE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB4-T2-EVIDENCE-PACKAGE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB4-T3-GO-NO-GO-DRAFT` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB4-T3-GO-NO-GO-DRAFT` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB5-T1-ACCEPTANCE-PACKAGE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB5-T1-ACCEPTANCE-PACKAGE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB5-T2-STRICT-MILESTONE-GATE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB5-T2-STRICT-MILESTONE-GATE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB5-T3-LAUNCH-RECOMMENDATION` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-BUSINESS-MB5-T3-LAUNCH-RECOMMENDATION` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-REL1-T1-RELEASE-NOTES` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-REL1-T1-RELEASE-NOTES` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-REL1-T2-SIGNOFF-PACKAGE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-REL1-T2-SIGNOFF-PACKAGE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO1-T1-LAUNCH-REHEARSAL` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO1-T1-LAUNCH-REHEARSAL` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO1-T2-POST-LAUNCH-CHECKLIST` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO1-T2-POST-LAUNCH-CHECKLIST` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO2-T1-STABILITY-OBSERVATION` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO2-T1-STABILITY-OBSERVATION` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO2-T2-OBSERVATION-QUEUE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO2-T2-OBSERVATION-QUEUE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO3-T1-TARGET-VALIDATION` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-FLOW-FULL-RUN-ASSESSMENT` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-MAIN-FLOW-FULL-RUN-ASSESSMENT` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO3-T1-TARGET-VALIDATION` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO3-T2-RECOVERY-TAXONOMY` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO3-T2-RECOVERY-TAXONOMY` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO4-T1-PROVIDER-REMEDIATION` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO4-T1-LOCAL-CODEX-CONFIG-ALIGNMENT` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO4-T1-LOCAL-CODEX-CONFIG-ALIGNMENT` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO4-T1-PROVIDER-REMEDIATION` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO4-T2-RERUN-VALIDATION-BUNDLE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO4-T2-RERUN-VALIDATION-BUNDLE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-DOCS-FULL-CONSOLIDATION` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-DOCS-FULL-CONSOLIDATION` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-SECRET-LEAK-GATE` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-SECRET-LEAK-GATE` completed (`done`)
- 2026-03-06 `DOC-2026-03-06-GO5-OPS-CHECKPOINT` started (`doing`)
- 2026-03-06 `DOC-2026-03-06-GO5-OPS-CHECKPOINT` completed (`done`)
