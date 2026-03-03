# Change Report: K4 release artifacts and approval switch

Date: 2026-03-01

## 1. Goal

- Continue execution without waiting for phase-by-phase confirmation.
- Complete K4 backlog:
  - `K4-T1` release artifacts
  - `K4-T2` release approval switch
  - `K4-T3` run-level gates/artifacts queries

## 2. Plan update

- Updated `PLAN.md` with K4 start/completion records.
- Updated `docs/v3_task_board.md`:
  - `K4-T1` -> `done`
  - `K4-T2` -> `done`
  - `K4-T3` -> `done`

## 3. Implementation

- Scheduler enhancements (`control_center/services/workflow_scheduler.py`):
  - added waiting-approval transition in `tick()`
  - added `approve_workitem()`
  - added artifact storage APIs:
    - `create_artifact()`
    - `list_artifacts()`
  - run status now includes `waiting_approval`
  - dependency satisfaction now accepts `skipped` upstream nodes
- Workflow engine enhancements (`control_center/services/workflow_engine.py`):
  - added `release_requires_approval` switch
  - bootstrap marks `release-manager` as `requires_approval` when enabled
  - execute response now includes waiting approval counts/ids
  - emits artifacts:
    - acceptance -> `acceptance_report`
    - release-manager -> `release_note` + `rollback_plan`
- API enhancements (`control_center/main.py`):
  - `GET /v3/workflows/runs/{run_id}/artifacts`
  - `POST /v3/workflows/workitems/{workitem_id}/approve`
  - existing gate query endpoint preserved
- Model/API contract enhancements:
  - `ApproveWorkItemRequest`
  - `ExecuteWorkflowRunResponse.waiting_approval_*` fields
- Docs:
  - `docs/protocol.md` updated with artifacts/approval endpoints and semantics
  - `docs/runbook.md` updated with approval and artifact commands

## 4. Verification

- Targeted:
  - `control_center/.venv/bin/pytest -q tests/unit/test_workflow_scheduler.py tests/unit/test_workflow_engine.py tests/unit/test_v3_workflow_engine_api.py tests/unit/test_openapi_contract.py`
- Full:
  - `control_center/.venv/bin/python scripts/update_openapi_snapshot.py`
  - `control_center/.venv/bin/pytest -q`
  - result: `100 passed`

## 5. Risks / follow-up

- Artifacts are metadata records only; file content generation is still stub path-based.
- v3 persistence is still in-memory; restart loses run/workitem/gate/discussion/artifact state.
- Next phase should focus on M5 production-readiness: persistence + observability + ops guardrails.
