# DOC-2026-03-05-OPS-REPORTS-BASELINE-CONSOLIDATION

## Scope

- Add stable entry index for `docs/ops_reports/`.
- Define retention rule separating latest pointers, milestone evidence, and disposable generated artifacts.
- Keep `ops_reports` as runtime evidence only, not planning source.

## Changed Files

- `PLAN.md`
- `docs/README.md`
- `docs/ops_reports/README.md`
- `docs/ops_reports/INDEX.md`

## Validation

- `rg -n "Purpose: generated runtime artifacts|Stable entry|Planning source" docs/ops_reports/README.md docs/ops_reports/INDEX.md docs/README.md`
- `rg -n "risk and follow-up|建议模板|变更目标|计划更新|实施改动|验证结果|风险与后续事项" docs/ops_reports docs/change_reports/README.md` (no matches)
