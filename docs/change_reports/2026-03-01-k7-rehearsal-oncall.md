# 2026-03-01 K7 Rehearsal + Oncall

## Goal

- Build practical production rehearsal tooling after K6 persistence:
  - restart recovery drill
  - parallel workflow probe
  - oncall checklist

## Plan updates

- `PLAN.md`
  - Added `Sprint-K7` tasks (`K7-T1/T2/T3`)
  - Marked K7 started and completed records
- `docs/v3_task_board.md`
  - Added K7 tasks and marked all K7 items `done`

## Changes

1. New recovery drill script
   - File: `scripts/v3_recovery_drill.sh`
   - Behavior:
     - starts isolated control-center with SQLite backend
     - runs a full v3 workflow to terminal
     - restarts control-center process
     - verifies run/gates/artifacts are unchanged after restart

2. New parallel probe script
   - File: `scripts/v3_parallel_probe.sh`
   - Behavior:
     - launches configurable concurrent workflow runs
     - auto-handles discussion resolve + approval paths
     - outputs per-run status and aggregate summary
     - strict mode fails on non-succeeded runs

3. Ops checklist and docs indexing
   - Added `docs/oncall_checklist.md`
   - Updated:
     - `docs/runbook.md`
     - `docs/README.md`
     - `scripts/README.md`

## Validation

- Script syntax check:
  - `bash -n scripts/v3_recovery_drill.sh`
  - `bash -n scripts/v3_parallel_probe.sh`
- Test regression:
  - `control_center/.venv/bin/pytest -q`
  - Result: `102 passed`

## Risk / follow-up

- `v3_recovery_drill.sh` runs an isolated control-center on a separate port; if local policy blocks spawning processes, run it in CI agent or allowlist environment.
