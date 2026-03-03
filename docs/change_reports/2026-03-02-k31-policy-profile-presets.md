# 2026-03-02 K31 Policy Profile Presets

## Goal

- Add reusable policy profiles for verification and preflight gates.
- Expose effective policy snapshot in runtime outputs.

## Plan updates

- Updated `PLAN.md`:
  - marked K31 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K31 tasks as `done`

## Changes

1. Policy profile presets
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--policy-profile strict|standard|degraded|custom`
   - Behavior:
     - applies default resolver and SLO policy bundles
     - explicit CLI options override profile defaults
     - mode guard: profile requires `--verify-manifest` or `--signer-preflight`

2. Effective policy observability
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added output fields:
     - `policy_profile`
     - `effective_policy`
   - `effective_policy` includes active resolver allowlist and SLO thresholds.

3. Profile-aware gates
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Preflight:
     - supports profile-driven history SLO gates
     - returns `policy_passed` + `slo_violations`
   - Verify:
     - supports profile-driven resolver and trend SLO gates
     - returns non-zero on policy gate failure

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - profile mode guard
     - preflight non-custom profile requires history
     - strict profile blocks fetch-hook resolver
     - degraded profile allows fetch-hook fallback
     - SLO gate behavior remains enforced with profile defaults

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - profile-based command examples
     - profile + manual override guidance
     - oncall commands moved to profile-first usage

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `33 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `17 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `151 passed`

## Risk / follow-up

- Profiles are currently CLI-scoped and not persisted globally.
- Next step: add centralized policy profile storage and runtime profile distribution.
