# DOC-2026-03-06-GO1-T1-LAUNCH-REHEARSAL

## Scope

- Execute GO1-T1 launch rehearsal for local scope.
- Validate release baseline and key workflow route sanity.
- Record rehearsal evidence and logs.

## Changed Files

- `PLAN.md`
- `docs/ops_reports/20260306T140423Z-go1-release-rehearsal.log`
- `docs/ops_reports/20260306T140423Z-go1-key-route-sanity.log`
- `docs/ops_reports/20260306T140423Z-go1-recovery-drill-attempt.json`
- `docs/ops_reports/20260306T140423Z-go1-recovery-drill-attempt.log`
- `docs/ops_reports/20260306T140423Z-go1-launch-rehearsal.md`

## Validation

- `bash scripts/check_all.sh release`
- `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py`
