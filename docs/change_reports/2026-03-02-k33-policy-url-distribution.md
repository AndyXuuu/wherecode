# 2026-03-02 K33 Policy URL Source + Effective Policy Distribution

## Goal

- Add URL-based policy source loading for verify/preflight policy profiles.
- Add automatic effective-policy distribution output for downstream nodes.

## Plan updates

- Updated `PLAN.md`:
  - marked K33 continued and completed
- Updated `docs/v3_task_board.md`:
  - marked K33 tasks as `done`

## Changes

1. Policy URL source adapter
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added options:
     - `--policy-source-url <url>`
     - `--policy-source-timeout <seconds>`
   - Behavior:
     - supports `file://` and `http(s)` JSON policy payload
     - validates timeout (`>=1`) and payload schema
     - merges source profile defaults into builtin profiles
     - output now includes policy source metadata:
       - `policy_source` (`builtin`/`policy_file`/`policy_url`)
       - `policy_source_descriptor`
       - `policy_source_url`
       - `policy_source_timeout`

2. Effective policy distribution
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added option:
     - `--distribute-effective-policy-dir <dir>`
   - Behavior:
     - available in `--verify-manifest` and `--signer-preflight` modes
     - writes:
       - `latest.json`
       - timestamped version file (`effective_policy_<mode>_<timestamp>.json`)
     - result payload includes:
       - `effective_policy_distribution_dir`
       - `effective_policy_distribution_latest`
       - `effective_policy_distribution_versioned`

3. Argument wiring hardening
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Fixed Python argv index mapping after K33 option insertion.
   - Added mode guards:
     - `--policy-source-url` requires verify/preflight mode
     - `--policy-file` and `--policy-source-url` conflict
     - `--distribute-effective-policy-dir` requires verify/preflight mode

4. Tests
   - File: `tests/unit/test_metrics_rollback_approval_gc.py`
   - Added coverage for:
     - policy-source-url mode guard
     - policy-file/policy-source-url conflict guard
     - distribute-effective-policy-dir mode guard
     - policy source URL profile loading (`file://`)
     - effective policy distribution output files and payload

5. Docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - policy source URL usage examples
     - policy source timeout usage
     - automatic effective-policy distribution usage

## Validation

- Syntax:
  - `bash -n scripts/v3_metrics_rollback_approval_gc.sh`
- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py`
  - Result: `42 passed`
- Compatibility:
  - `control_center/.venv/bin/pytest -q tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py`
  - Result: `17 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `160 passed`

## Risk / follow-up

- URL source currently fetches on-demand per script execution; no cache layer yet.
- Next step: expose policy source/distribution state through API for centralized rollout visibility.
