# WhereCode: Cross-Space AI Collaboration Command Center

> Fuel the machine: this project is AI-built. To support high-quality output and MCP boundary exploration, sponsor tokens or API credits.
> Contact: [andy1770@proton.me](mailto:andy1770@proton.me)

WhereCode is a personal developer workflow architecture. It moves intent input to mobile devices, keeps the PC as execution hub, and coordinates multiple AI collaborators.

[English](./README.md) | [简体中文](./README.zh-CN.md)

## V2 Snapshot

## AI Ownership

- AI executes end-to-end delivery.
- User provides goals/suggestions only.

## V2 Positioning

V2 aligns to OpenClaw / OpenCode / Oh My OpenCode style operation:
- one command starts the run
- plan/build modes
- autonomous loop with structured artifacts
- milestone checkpoint before release decision

## Architecture

1. `command_center/`
- Input and visibility.

2. `control_center/`
- Main brain: decompose, schedule, gate, recover, persist.

3. `action_layer/`
- Execution provider/runtime.

4. `project/<key>/`
- Rebuildable subproject workspace.
- Requirement file is source of truth.

Detailed docs:
- `docs/ARCHITECTURE_V2.md`
- `docs/OPERATIONS_V2.md`
- `docs/V2_PROJECT_PLAN.md`
- `docs/V2_PROJECT_PLAN.zh-CN.md`

## Core Commands

```bash
# main project orchestration path
bash scripts/stationctl.sh main-orchestrate
bash scripts/stationctl.sh plan-autopilot
bash scripts/stationctl.sh plan-autopilot --max-tasks 3
bash scripts/check_all.sh main

# v2 requirement-driven path
bash scripts/stationctl.sh v2-run stock-sentiment
bash scripts/stationctl.sh v2-run stock-sentiment --mode plan
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode test
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode dev --reset-dev-state true
bash scripts/stationctl.sh v2-run stock-sentiment --mode build --workflow-mode dev
bash scripts/check_all.sh v2

# unified check api (remote progress)
bash scripts/check_all.sh v2 --async
curl "http://127.0.0.1:8000/ops/checks/latest?scope=v2" -H "X-WhereCode-Token: change-me"
```

Codex app slash entry:

```text
/plan-autopilot
/plan-autopilot-strict
```

## Requirement Input

- Canonical: `project/requirements/stock-sentiment.md`
- Runtime snapshot: `project/stock-sentiment/REQUIREMENTS.md`

## Reusable Capability Packaging

- Registry: `control_center/capabilities/registry.json`
- Contract schema: `control_center/capabilities/capability_contract.schema.json`
- Developer routing matrix: `control_center/capabilities/dev_routing_matrix.json`
- Templates: `control_center/capabilities/templates/*.manifest.json`
- Local check:
  - `python3 scripts/capability_contract_check.py`
  - `python3 scripts/capability_contract_check.py --manifest control_center/capabilities/templates/agent.manifest.json`
  - `python3 scripts/dev_routing_matrix_check.py`

## License

Licensed under GNU Affero General Public License v3.0 (AGPL-3.0).
See `LICENSE`.
