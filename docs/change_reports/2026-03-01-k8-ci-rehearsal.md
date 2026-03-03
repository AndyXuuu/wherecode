# 2026-03-01 K8 CI Rehearsal Automation

## Goal

- Move v3 rehearsal from manual operation to CI execution:
  - one-command rehearsal script
  - GitHub Actions integration
  - docs update for usage and parameters

## Plan updates

- `PLAN.md`
  - Added `Sprint-K8` with `K8-T1/T2/T3`
  - Marked K8 started/completed
- `docs/v3_task_board.md`
  - Added K8 tasks and marked all as `done`

## Changes

1. New CI rehearsal script
   - File: `scripts/ci_v3_rehearsal.sh`
   - Flow:
     1) ensure action-layer/control-center running
     2) run `http_async_smoke.sh`
     3) run `action_layer_smoke.sh`
     4) run `v3_workflow_smoke.sh`
     5) run `v3_parallel_probe.sh`
     6) run `v3_recovery_drill.sh`
   - Includes cleanup trap to stop services started by the script.

2. CI workflow integration
   - File: `.github/workflows/ci.yml`
   - Added `backend-rehearsal` job:
     - setup Python
     - install backend deps
     - execute `scripts/ci_v3_rehearsal.sh`
     - configurable probe size via env vars

3. Docs updates
   - Updated:
     - `docs/runbook.md`
     - `scripts/README.md`
   - Added CI rehearsal command and key environment variables.

## Validation

- Syntax checks:
  - `bash -n scripts/ci_v3_rehearsal.sh scripts/v3_recovery_drill.sh scripts/v3_parallel_probe.sh`
- Regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `102 passed`

## Notes

- Local full rehearsal execution was blocked in this sandbox because opening localhost listener ports returned `PermissionError: [Errno 1] Operation not permitted`.
- The script is intended for normal local dev shells and CI runners where port binding is available.
