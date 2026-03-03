# TST1-T2 rollback/policy regression (2026-03-03)

## Commands

- `PUT /metrics/workflows/alert-policy` with policy A.
- `PUT /metrics/workflows/alert-policy` with policy B.
- `GET /metrics/workflows/alert-policy/audits?limit=10`.
- `bash scripts/v3_metrics_policy_rollback.sh <audit_id> --dry-run`.
- `bash scripts/v3_metrics_policy_rollback.sh <audit_id>` with idempotency key.
- replay same rollback command with same idempotency key.
- `bash scripts/v3_metrics_rollback_approval_gc.sh --dry-run`.
- `bash scripts/v3_metrics_report.sh`.
- `bash scripts/v3_metrics_alert_check.sh`.
- `GET /metrics/workflows/alert-policy/verify-policy/export`.

## Result

- policy update regression: passed.
- rollback dry-run regression: passed.
- rollback apply regression: passed.
- rollback idempotent replay regression: passed (`idempotent_replay=true`).
- approval gc script regression: passed.
- metrics report regression: passed.
- alert policy check regression: passed (`triggered=false`).
- verify policy export regression: passed.

## Notes

- first rollback apply attempt failed with `409` when rollback target matched current policy.
- fixed by creating two policy revisions and rolling back to the previous revision.
