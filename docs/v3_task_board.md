# v3 Task Board (Active + Release)

Updated: 2026-03-03

## 1) Status

- `todo`
- `doing`
- `blocked`
- `done`

## 2) Active Sprint: TST2

| ID | Task | Owner | Depends | Status |
| --- | --- | --- | --- | --- |
| TST2-T1 | stability soak test (24h metrics drift) | qa-test | TST1-T3 | doing |
| TST2-T2 | release rehearsal + rollback drill | release-manager | TST2-T1 | todo |
| TST2-T3 | oncall checklist signoff | security-review | TST2-T2 | todo |

## 3) Release Track

| Stage | Gate | Status |
| --- | --- | --- |
| M-TEST-ENTRY | `v3_milestone_gate.sh --strict` | passed |
| TST1 | integration matrix + policy regression | done |
| TST2 | soak + rehearsal + oncall signoff | doing |
| REL1 | acceptance + release package | todo |
| GO1 | go-live checklist | todo |

## 4) Next Action

- Monitor live `TST2-T1` soak and run `tst2_soak_status.sh --strict`.
