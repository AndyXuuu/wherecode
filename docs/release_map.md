# Release Map (v3)

Updated: 2026-03-03

## 1) Objective

- Move from `TST1` to `GO1` with auditable gates.
- Keep role-based execution and no gate bypass.

## 2) Stage Map

| Stage | Scope | Required Output | Gate |
| --- | --- | --- | --- |
| M-TEST-ENTRY | test phase admission | milestone result JSON | `bash scripts/v3_milestone_gate.sh --milestone test-entry --strict` |
| TST1 | integration matrix | smoke/recovery/probe results | `TST1-T1/T2/T3` done |
| TST2 | hardening + rehearsal | soak metrics + release rehearsal logs | `ci_v3_rehearsal.sh` green |
| REL1 | release signoff | acceptance report + release note + rollback plan | signoff artifacts complete |
| GO1 | production launch | go-live checklist + oncall handoff | all launch checks green |

## 3) Role Ownership

| Area | Primary Role | Backup Role |
| --- | --- | --- |
| Orchestration and split | chief-architect | release-manager |
| Module implementation | module-dev | chief-architect |
| Docs consistency | doc-manager | module-dev |
| Test and matrix | qa-test | release-manager |
| Security and risk | security-review | chief-architect |
| Final acceptance | acceptance | release-manager |
| Release execution | release-manager | qa-test |

## 4) Current Position

- `M-TEST-ENTRY`: passed.
- `TST1`: completed.
- `TST2`: in progress (`TST2-T1` doing).
- `REL1/GO1`: pending.

## 5) Immediate Run List

```bash
bash scripts/http_async_smoke.sh
bash scripts/action_layer_smoke.sh
bash scripts/full_stack_smoke.sh
bash scripts/v3_workflow_smoke.sh
bash scripts/v3_recovery_drill.sh
bash scripts/v3_parallel_probe.sh http://127.0.0.1:8000 6 3
bash scripts/ci_v3_rehearsal.sh
SOAK_DURATION_SECONDS=86400 SOAK_INTERVAL_SECONDS=300 bash scripts/tst2_soak.sh
bash scripts/tst2_soak_status.sh --strict
```
