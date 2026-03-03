# 2026-03-02 K32 Policy File Loading + Effective Policy Export

## Goal

- Add centralized policy-file loading for profile defaults.
- Add effective-policy snapshot export for downstream distribution.

## Plan updates

- Updated `PLAN.md`:
  - marked K32 started and completed
- Updated `docs/v3_task_board.md`:
  - marked K32 tasks as `done`

## Changes

1. Policy file loading
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--policy-file <file>`
   - Behavior:
     - loads `default_profile` + `profiles` override map from JSON file
     - merges file profiles over builtin `strict/standard/degraded/custom`
     - supports file-driven default profile selection when `--policy-profile` is omitted

2. Effective policy export
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--export-effective-policy <file>`
   - Behavior:
     - exports generated snapshot with mode + effective policy payload
     - available in both `--verify-manifest` and `--signer-preflight` modes
     - result payload includes `effective_policy_path`

3. Profile and policy observability hardening
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `effective_policy.policy_file`
     - `effective_policy.policy_source` (`builtin` / `policy_file`)
     - preflight/verify mode guards for policy-file/export-effective-policy

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - `--policy-file` mode guard
     - `--export-effective-policy` mode guard
     - policy-file default profile application
     - effective policy snapshot export content

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - policy-file usage examples
     - effective-policy export command examples
     - option matrix updates for K32 options

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `37 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `17 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `155 passed`

## Risk / follow-up

- Policy file currently works as local file input; no runtime sync or API registry yet.
- Next step: add API-level policy profile endpoint and automated distribution to operational nodes.
