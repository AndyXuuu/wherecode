# REL1 发布说明（主业务）

日期：2026-03-06
范围：单机本地部署

## 摘要

- MB5 收口后，发布阶段推进至 `REL1`。
- 主流程链路已形成并留证：`command -> orchestrate -> recover -> execute`。
- 严格里程碑门禁通过：`tst2-ready --strict`。

## 本次 REL1 包含内容

- MB3 dry-run + recover + execute 全链路证据。
- MB4 发布就绪证据包与 go/no-go 草案。
- MB5 验收包与上线建议（`GO`）。
- chief 非成功返回时的合成分解兜底（默认开启）。

## 运行条件

- 保持 `WHERECODE_DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK=true`。
- 每次发布切面前执行 `bash scripts/check_all.sh release`。
- 当分解进入确认态时，保持人工确认步骤。

## 校验快照

- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`：通过。
- 当前建议：推进到 `REL1` release signoff。

## 已知限制

- 外部 provider 波动仍可能影响分解/输出质量。
- 本次签发仅针对单机本地范围，不代表多机高可用就绪。

## 参考

- `docs/ops_reports/20260306T135435Z-mb5-acceptance-package.md`
- `docs/ops_reports/20260306T135435Z-mb5-launch-recommendation.md`
- `docs/ops_reports/20260306T134912Z-mb4-readiness-package.md`
- `docs/ops_reports/20260306T134912Z-mb4-go-no-go-draft.md`
- `docs/ops_reports/20260306T134242Z-mb3-t5-full-loop.json`
