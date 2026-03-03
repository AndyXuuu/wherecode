# Change Report: K1-T2 role registry

Date: 2026-03-01

## 1. Goal

- Implement K1-T2 from v3 backlog.
- Add role -> executor registry with explicit unknown-role error behavior.

## 2. Plan update

- Updated `PLAN.md`:
  - marked K1-T2 started
  - marked K1-T2 completed with verification commands
- Updated `docs/v3_task_board.md`:
  - changed K1-T2 status from `doing` to `done`

## 3. Implementation

- Added `action_layer/services/agent_registry.py`:
  - `AgentRegistry` with default role mapping
  - register/resolve/has_role/list_roles/as_dict methods
  - normalization for role/executor strings
  - overwrite control for duplicate registration
  - `UnknownAgentRoleError` for unknown role lookup
  - `RegisteredAgent` helper model
- Added `action_layer/services/__init__.py` exports.
- Added `tests/unit/test_agent_registry.py`:
  - 7 tests for default mapping, normalization, unknown role, register behavior, and invalid input checks.

## 4. Verification

- `control_center/.venv/bin/pytest -q tests/unit/test_agent_registry.py`
  - result: `7 passed`
- `control_center/.venv/bin/pytest -q tests/unit`
  - result: `66 passed`

## 5. Risks / follow-up

- Registry exists but is not wired into Action Layer runtime dispatch yet.
- Next task: K1-T3 (`agent.md` isolation loader) and then bind role resolution into runtime execute flow.
