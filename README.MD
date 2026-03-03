# WhereCode

Multi-agent software delivery system with role-based orchestration.

[English](./README.md) | [简体中文](./README.zh-CN.md)

## One-Pager (2026-03-03)

### Positioning

- Main path: `Project -> Task -> Command` (HTTP async).
- Runtime architecture:
  - `Command Center` (UI)
  - `Control Center` (orchestration, policy, gates)
  - `Action Layer` (role agents)

### Delivered

- Workflow run/workitem orchestration with dependency scheduling.
- Role pipeline:
  - `module-dev -> doc-manager -> qa-test -> security-review -> acceptance -> release-manager`
- Discussion control (budget/timeout/loop fingerprint).
- Gate checks (doc/test/security) + module reflow.
- Metrics and policy governance (audit + rollback approval).
- Milestone gate: `scripts/v3_milestone_gate.sh`.
- SQLite state persistence + restart recovery.

### Current phase

- `K1-K50`: done
- `M-TEST-ENTRY`: passed
- active sprint: `TST1`

### Go-live gates

- TST matrix green.
- Rollback/policy regression green.
- Acceptance + release signoff complete.
- Oncall checklist complete.

## Quick start

```bash
bash scripts/stationctl.sh install all
bash scripts/stationctl.sh dev all
bash scripts/check_all.sh
```

## Active docs

- release stages: `docs/release_map.md`
- active plan: `PLAN.md`
- task board: `docs/v3_task_board.md`
- system spec: `docs/system_spec.md`
- API protocol: `docs/protocol.md`
- runbook: `docs/runbook.md`
- oncall checklist: `docs/oncall_checklist.md`
- troubleshooting: `docs/troubleshooting.md`

## License

AGPL-3.0. See `LICENSE`.
