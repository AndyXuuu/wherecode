# TST1 acceptance + release signoff (2026-03-03)

## Scope

- Sprint: `TST1`
- Items:
  - `TST1-T1` smoke/recovery/probe matrix
  - `TST1-T2` rollback/policy gate regression
  - `TST1-T3` acceptance + signoff

## Evidence

- matrix report: `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/2026-03-03-tst1-t1-matrix.md`
- policy regression report: `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/2026-03-03-tst1-t2-policy-regression.md`
- workflow metrics report: `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/2026-03-03-workflow-metrics.md`
- verification check: `bash scripts/check_all.sh` (`205 passed` + frontend build passed)

## Gate status

- `M-TEST-ENTRY`: passed.
- TST1 matrix gate: passed.
- rollback/policy regression gate: passed.
- acceptance review gate: passed.

## Release signoff

- decision: approved to enter `TST2`.
- required follow-up:
  - run `TST2-T1` stability soak test (24h metrics drift).
  - keep rollback idempotency key policy in release rehearsal.
