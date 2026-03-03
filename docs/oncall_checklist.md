# Oncall Checklist (Active)

Updated: 2026-03-03

## 1) Shift start checks

```bash
curl http://127.0.0.1:8000/healthz
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/action-layer/health
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/metrics/workflows
curl -H "X-WhereCode-Token: ${WHERECODE_TOKEN:-change-me}" http://127.0.0.1:8000/metrics/summary
```

- Confirm runtime uses sqlite:
  - `WHERECODE_STATE_BACKEND=sqlite`
  - `WHERECODE_SQLITE_PATH` exists and writable.

## 2) Daily ops commands

```bash
bash scripts/v3_metrics_report.sh
bash scripts/v3_metrics_alert_check.sh
bash scripts/v3_metrics_rollback_approval_gc.sh --dry-run
bash scripts/tst2_soak_status.sh --strict
```

If policy rollback needed:

```bash
bash scripts/v3_metrics_policy_rollback.sh <audit_id> --dry-run
```

## 3) Pre-release gate checks

```bash
bash scripts/v3_milestone_gate.sh --milestone test-entry --strict
bash scripts/http_async_smoke.sh
bash scripts/v3_workflow_smoke.sh
bash scripts/v3_recovery_drill.sh
bash scripts/v3_parallel_probe.sh http://127.0.0.1:8000 6 3
```

## 4) Incident severity

- `SEV-1`: API unavailable, data corruption risk, rollback impossible.
- `SEV-2`: core workflow blocked, gate failure surge, persistent retries.
- `SEV-3`: single module failure, local degradation, workaround exists.

## 5) Incident response

1. Freeze risky changes and capture request IDs.
2. Run smoke + metrics snapshot.
3. If policy issue, rollback with approved role.
4. If unresolved in 30 minutes, escalate to release-manager.

## 6) References

- Full policy/verify/restore command options: `scripts/README.md`
- Troubleshooting playbook: `docs/troubleshooting.md`
- Release stages: `docs/release_map.md`
