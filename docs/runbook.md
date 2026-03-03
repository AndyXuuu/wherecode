# Runbook (Active)

Updated: 2026-03-03

## 1) Standard command entry

Use root scripts. Do not install mixed dependencies at repository root.

```bash
bash scripts/stationctl.sh install all
bash scripts/stationctl.sh dev all
bash scripts/stationctl.sh start all
bash scripts/stationctl.sh status all
bash scripts/stationctl.sh stop all
bash scripts/stationctl.sh check
```

## 2) Minimal env baseline

```bash
export WHERECODE_TOKEN=change-me
export WHERECODE_STATE_BACKEND=sqlite
export WHERECODE_SQLITE_PATH=.wherecode/state.db
```

Optional:

```bash
export WHERECODE_RELEASE_APPROVAL_REQUIRED=true
export WHERECODE_AGENT_ROUTING_FILE=control_center/agents.routing.json
```

## 3) Health and contract checks

```bash
curl http://127.0.0.1:8000/healthz
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/action-layer/health
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/metrics/summary
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/metrics/workflows
control_center/.venv/bin/pytest -q
bash scripts/check_all.sh
```

If API schema changed:

```bash
control_center/.venv/bin/python scripts/update_openapi_snapshot.py
control_center/.venv/bin/pytest -q
```

## 4) Smoke and rehearsal set

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

Milestone gate:

```bash
bash scripts/v3_milestone_gate.sh --milestone test-entry --strict
```

## 5) Metrics and policy operations

```bash
bash scripts/v3_metrics_report.sh
bash scripts/v3_metrics_alert_check.sh
bash scripts/v3_metrics_policy_rollback.sh <audit_id> --dry-run
bash scripts/v3_metrics_rollback_approval_gc.sh --dry-run
```

Policy API:

```bash
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  http://127.0.0.1:8000/metrics/workflows/alert-policy
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  http://127.0.0.1:8000/metrics/workflows/alert-policy/audits?limit=20
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" \
  http://127.0.0.1:8000/metrics/workflows/alert-policy/rollback-approvals/stats
```

## 6) References

- Full script flags: `scripts/README.md`
- System roles and state model: `docs/system_spec.md`
- Active release path: `docs/release_map.md`
- Task board: `docs/v3_task_board.md`
- Troubleshooting: `docs/troubleshooting.md`
