# WhereCode: AI Engineering Control Plane (V3)

> Fuel the machine: this project is AI-built. To support high-quality output and MCP boundary exploration, sponsor tokens or API credits.
> Contact: [andy1770@proton.me](mailto:andy1770@proton.me)

WhereCode is a control plane for autonomous software delivery.
It orchestrates requirements, stage gates, role routing, evidence, and reports.
Execution is delegated to external engines (OpenCode / OhMyOpenCode) through stable adapters.

[English](./README.md) | [简体中文](./README.zh-CN.md)

## V3 Snapshot

- Single adapter execution plane: `opencode` with dual strategy routing (`native|ohmy`).
- Hard-cut V3 command surface in `stationctl` (no `v2-*`/`subproject-*` execution entries).
- Clarification + SDD + acceptance gates in workflow runtime:
  - `requirement_status`
  - `clarification_rounds`
  - `assumption_used`
- Remote visibility APIs:
  - `GET /v3/runs/{id}/timeline`
  - `GET /v3/runs/{id}/artifacts`
  - `GET /v3/runs/{id}/report`

## AI Ownership

- AI executes end-to-end delivery.
- User provides goals/suggestions only.

## Positioning

- Main project owns orchestration and acceptance gates.
- External executors own code-generation/edit execution.
- User provides goal/suggestion only; AI executes end-to-end.

## Architecture

1. `command_center/`
- Input and visibility.

2. `control_center/`
- Main brain: decompose, schedule, gate, recover, persist.

3. `action_layer/`
- Thin execution gateway (request normalization + forwarding).

4. `project/<key>/`
- Rebuildable subproject workspace.
- Requirement file is source of truth.

5. `external/executors/`
- Local checkout workspace for OpenCode / OhMyOpenCode upstream updates.
- External source is isolated from control-plane code.

6. `.agents/`
- Role rules, reusable skills, routing/context policies, MCP configs.
- Canonical role profile path: `.agents/roles/<role>/AGENTS.md`.

Detailed docs:
- `docs/V3_PROJECT_PLAN.md`
- `docs/V3_ENGINEERING_LAYOUT.md`
- `docs/STANDARD_AGENT_REACT.md`

## Core Commands

```bash
# main project orchestration path
bash scripts/stationctl.sh main-orchestrate
bash scripts/stationctl.sh plan-autopilot
bash scripts/stationctl.sh plan-autopilot --max-tasks 3
bash scripts/check_all.sh main
```

Codex app slash entry:

```text
/plan-autopilot
/plan-autopilot-strict
```

## Requirement Input

- Canonical: `project/requirements/stock-sentiment.md`

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
