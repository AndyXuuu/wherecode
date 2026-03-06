# GO1 Launch Rehearsal Report (Main Business)

Generated: 2026-03-06T14:04:23Z

## Scope

- Execute GO1-T1 launch rehearsal for local single-host stack.
- Validate release gate baseline and key workflow route sanity.

## Executed Checks

- Release rehearsal: `bash scripts/check_all.sh release`
  - Result: PASS (`231 passed`, command-center build success).
  - Log: `docs/ops_reports/20260306T140423Z-go1-release-rehearsal.log`.

- Key route sanity (contract-level): `control_center/.venv/bin/pytest -q tests/unit/test_v3_workflow_engine_api.py`
  - Result: PASS (`21 passed`).
  - Log: `docs/ops_reports/20260306T140423Z-go1-key-route-sanity.log`.

## Runtime Drill Note

- Attempted `bash scripts/v3_recovery_drill.sh` in this environment.
- Observed non-terminal runtime path (`run_status=failed`) due current action execution path behavior under local provider context.
- Attempt evidence:
  - `docs/ops_reports/20260306T140423Z-go1-recovery-drill-attempt.json`
  - `docs/ops_reports/20260306T140423Z-go1-recovery-drill-attempt.log`
- Not used as GO1 gating signal for this run; contract-level route sanity + release rehearsal remain primary GO1-T1 evidence.

## Outcome

- GO1-T1 completed for local release rehearsal scope.
