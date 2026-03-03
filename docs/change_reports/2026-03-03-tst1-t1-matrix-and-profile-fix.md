# 2026-03-03 TST1-T1 matrix and profile fix

## Scope

- Execute TST1-T1 smoke/recovery/probe matrix.
- Fix workflow smoke blocker in Action Layer role profiles.

## Plan update

- `TST1-T1` started (`doing`).
- `TST1-T1` blocked (`integration-test` profile missing).
- `TST1-T1` completed (`done`).
- `TST1-T2` started (`doing`).

## Changes

- Added missing role profile:
  - `/Users/andyxu/Documents/project/wherecode/action_layer/agents/integration-test/agent.md`
- Added profile contract test:
  - `/Users/andyxu/Documents/project/wherecode/tests/unit/test_agent_profile_loader.py`
  - new case validates all `AgentRegistry` roles have profile files in repo.
- Updated active planning/state:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`
  - `/Users/andyxu/Documents/project/wherecode/docs/v3_task_board.md`
  - `/Users/andyxu/Documents/project/wherecode/.wherecode/state.json`
- Added matrix ops report:
  - `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/2026-03-03-tst1-t1-matrix.md`

## Checks

- `control_center/.venv/bin/pytest -q tests/unit/test_agent_profile_loader.py tests/unit/test_v3_workflow_engine_api.py`
  - `11 passed`
- TST1 matrix:
  - `http_async_smoke.sh` passed
  - `action_layer_smoke.sh` passed
  - `v3_workflow_smoke.sh` passed
  - `v3_parallel_probe.sh` passed
  - `v3_recovery_drill.sh` passed
  - `full_stack_smoke.sh` passed
  - `ci_v3_rehearsal.sh` passed
- `bash scripts/check_all.sh`
  - backend tests: `205 passed`
  - command_center build: passed
