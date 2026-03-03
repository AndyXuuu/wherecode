# Change Report: K1-T6 overall flow runnable

Date: 2026-03-01

## 1. Goal

- Continue implementation until the overall v3 workflow can run end-to-end.
- Deliver a minimal closed loop: bootstrap pipeline from modules and execute to terminal state.

## 2. Plan update

- Updated `PLAN.md`:
  - added `K1-T6` in kickoff backlog
  - marked `K1-T6` started and completed
- Updated `docs/v3_task_board.md`:
  - set `K1-T6` status to `done`

## 3. Implementation

- Added orchestration engine:
  - `control_center/services/workflow_engine.py`
  - supports:
    - standard pipeline bootstrap from module list
    - ready-queue execution loop until blocked/terminal
    - role -> agent mapping via `AgentRegistry`
    - execution metadata writeback to workitem
- Extended v3 API models:
  - `BootstrapWorkflowRequest`
  - `ExecuteWorkflowRunRequest`
  - `ExecuteWorkflowRunResponse`
  - extended `ActionExecuteRequest` with `role` and `module_key`
  - extended `ActionExecuteResponse` with `metadata`
- Extended Control Center APIs:
  - `POST /v3/workflows/runs/{run_id}/bootstrap`
  - `POST /v3/workflows/runs/{run_id}/execute`
- Kept earlier v3 endpoints and connected them through engine/scheduler.
- Added role mapping for `integration-test` in registry.
- Updated Action Layer runtime:
  - role-aware execution input
  - agent profile isolation integration (`AgentProfileLoader`)
  - capability output now includes roles
- Updated docs:
  - `docs/protocol.md` v3 workflow section
  - `docs/runbook.md` runnable curl flow for v3 closed loop

## 4. Verification

- `control_center/.venv/bin/python scripts/update_openapi_snapshot.py`
- `control_center/.venv/bin/pytest -q`
  - result: `85 passed`
- Added/updated tests:
  - `tests/unit/test_workflow_engine.py`
  - `tests/unit/test_v3_workflow_engine_api.py`
  - `tests/unit/test_openapi_contract.py`
  - existing suite still green

## 5. Risks / follow-up

- Workflow engine is still in-memory (no persistent v3 run storage yet).
- Discussion budget protocol (K2) is not wired into execution flow yet.
- Gate execution is stage-based but not yet backed by dedicated gate executors (`doc/test/security`) from K3.
