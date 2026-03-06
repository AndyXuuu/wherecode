# GO1 Post-Launch Sanity & Rollback Checklist

Generated: 2026-03-06T14:04:23Z

## Scope

- Execute GO1-T2 post-launch sanity checklist on local stack.
- Confirm baseline service startup, health paths, and smoke flow execution.

## Checklist

- [x] Start all services with unified entry (`stationctl start all`).
- [x] Control health endpoint reachable (`/healthz`).
- [x] Action-layer health endpoint reachable (`/healthz`).
- [x] Control-to-action proxy health reachable (`/action-layer/health`).
- [x] Control async smoke flow executed.
- [x] Action-layer smoke flow executed.

## Evidence

- Command: `bash scripts/full_stack_smoke.sh`
- Result: PASS (`full stack smoke passed`).
- Log: `docs/ops_reports/20260306T140423Z-go1-full-stack-smoke.log`.

## Rollback Readiness

- Service control entry available: `bash scripts/stationctl.sh stop all` / `start all`.
- Release baseline command retained for rollback verification: `bash scripts/check_all.sh release`.

## Outcome

- GO1-T2 checklist completed for current local environment.
