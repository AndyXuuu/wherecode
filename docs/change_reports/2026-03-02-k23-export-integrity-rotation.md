# 2026-03-02 K23 Export Integrity + Rotation

## Goal

- Add integrity metadata to purge-audit export payloads.
- Add export file rotation workflow in CLI for long-term operations.

## Plan updates

- Updated `PLAN.md`:
  - marked K23 started/completed
  - added K24 backlog
- Updated `docs/v3_task_board.md`:
  - marked K23 tasks as `done`
  - set K24 as next action

## Changes

1. Export integrity metadata
   - Files:
     - `control_center/main.py`
     - `control_center/models/api.py`
     - `control_center/models/__init__.py`
   - Added:
     - export response includes `checksum_scope` and `checksum_sha256`
   - Behavior:
     - checksum computed from canonicalized export `entries` payload

2. CLI export integrity
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - export mode output includes checksum fields
     - output file retains checksum for downstream verification

3. Export rotation automation
   - File: `scripts/v3_metrics_rollback_approval_gc.sh`
   - Added:
     - `--rotate-exports`
     - `--export-dir`
     - `--retain-seconds`
     - `--keep-export-latest`
   - Safety:
     - rotation requires `--export-dir`
     - rotation requires at least one of retain/keep switches
     - rotation mode is mutually exclusive with purge/export modes

4. Tests and OpenAPI
   - Files:
     - `tests/unit/test_v3_metrics_alert_policy_api.py`
     - `tests/unit/test_metrics_rollback_approval_gc.py`
     - `tests/unit/test_openapi_contract.py`
     - `tests/snapshots/openapi.snapshot.json`
   - Added coverage for:
     - export checksum validation
     - rotate-exports behavior and safety check
     - OpenAPI schema fields for checksum metadata

5. Ops docs
   - Files:
     - `docs/runbook.md`
     - `docs/oncall_checklist.md`
     - `scripts/README.md`
   - Added:
     - checksum field guidance
     - rotate-exports commands and safety rules
     - oncall rotation checklist item

## Validation

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_metrics_rollback_approval_gc.py tests/unit/test_v3_metrics_alert_policy_api.py tests/unit/test_openapi_contract.py tests/unit/test_openapi_snapshot.py`
  - Result: `26 passed`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `126 passed`

## Risk / follow-up

- Export rotation does not yet maintain a manifest index.
- Next (K24): add manifest index + checksum verify workflow.
