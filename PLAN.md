# WhereCode PLAN (Active Only)

Updated: 2026-03-03

## 1) Workflow DNA

1. Update plan first.
2. Implement.
3. Run checks.
4. Update docs.

Task log rule:
- Start: `started (doing)`.
- Finish: `completed (done)`.
- Completed history is archived in `docs/change_reports/`.
- Keep PLAN only for active and next release work.

## 2) Active Sprint: TST2

| ID | Task | Owner | Depends | Status |
| --- | --- | --- | --- | --- |
| TST2-T1 | stability soak test (24h metrics drift) | qa-test | TST1-T3 | doing |
| TST2-T2 | release rehearsal + rollback drill | release-manager | TST2-T1 | todo |
| TST2-T3 | oncall checklist signoff | security-review | TST2-T2 | todo |

## 3) Release Map

| Stage | Goal | Exit Gate | Status |
| --- | --- | --- | --- |
| M-TEST-ENTRY | Enter integration test phase | `bash scripts/v3_milestone_gate.sh --milestone test-entry --strict` | passed |
| TST1 | Integration matrix + rollback/policy regression | `TST1-T1/T2/T3` all done | done |
| TST2 | Stability hardening + release rehearsal | full smoke + recovery + oncall drill green | doing |
| REL1 | Release package and signoff | acceptance report + release note + rollback plan | todo |
| GO1 | Production launch | go-live checklist all green | todo |

## 4) Gate Commands (Current Baseline)

- Full tests: `control_center/.venv/bin/pytest -q`
- Full checks: `bash scripts/check_all.sh`
- TST1 matrix:
  - `bash scripts/http_async_smoke.sh`
  - `bash scripts/action_layer_smoke.sh`
  - `bash scripts/full_stack_smoke.sh`
  - `bash scripts/v3_workflow_smoke.sh`
  - `bash scripts/v3_recovery_drill.sh`
  - `bash scripts/v3_parallel_probe.sh http://127.0.0.1:8000 6 3`
  - `bash scripts/ci_v3_rehearsal.sh`

## 5) Next Action

- Execute `DOC-2026-03-04-IGNORE-AND-COMMIT`.

## 6) Task Log (Active Window)

- 2026-03-03 `TST1-T1/T2/T3` started (`doing`)
- 2026-03-03 `DOC-2026-03-03-PLAN-RESET-RELEASE-MAP` started (`doing`)
- 2026-03-03 `DOC-2026-03-03-PLAN-RESET-RELEASE-MAP` completed (`done`)
- 2026-03-03 `DOC-2026-03-03-DOC-CONSOLIDATION` started (`doing`)
- 2026-03-03 `DOC-2026-03-03-DOC-CONSOLIDATION` completed (`done`)
- 2026-03-03 `TST1-T1` started (`doing`)
- 2026-03-03 `TST1-T1` blocked: `v3_workflow_smoke` failed (`integration-test` profile missing)
- 2026-03-03 `TST1-T1` completed (`done`)
- 2026-03-03 `TST1-T2` started (`doing`)
- 2026-03-03 `TST1-T2` blocked: rollback target matched current policy (`409`)
- 2026-03-03 `TST1-T2` completed (`done`)
- 2026-03-03 `TST1-T3` started (`doing`)
- 2026-03-03 `TST1-T3` completed (`done`)
- 2026-03-03 `TST2-T1` started (`doing`)
- 2026-03-03 `TST2-T1` soak automation started (`doing`)
- 2026-03-03 `TST2-T1` soak rehearsal completed (`done`)
- 2026-03-03 `TST2-T1` blocked: waiting 24h wall-clock soak window
- 2026-03-03 `TST2-T1` blocked: 24h background soak process not persistent in tool session
- 2026-03-03 `TST2-T1` 24h soak live session started (`doing`)
- 2026-03-04 `DOC-2026-03-04-TST2-SOAK-CHECKPOINT` started (`doing`)
- 2026-03-04 `DOC-2026-03-04-TST2-SOAK-CHECKPOINT` completed (`done`)
- 2026-03-04 `DOC-2026-03-04-IGNORE-AND-COMMIT` started (`doing`)
