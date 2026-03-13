# WhereCode V3 Overlap Audit (OpenCode + OhMyOpenCode)

Updated: 2026-03-13

## 1. Scope

Compare current WhereCode capabilities with:

- OpenCode CLI/runtime capabilities
- OhMyOpenCode plugin capabilities (agent/category orchestration)

Goal: remove duplicated execution responsibilities and keep WhereCode focused on control-plane value.

## 2. Capability Overlap Matrix

Scoring:

- overlap `high`: feature already strong in OpenCode/OhMy
- overlap `medium`: partially overlaps, but WhereCode still needs boundary logic
- overlap `low`: mostly WhereCode-unique, should be retained

| Capability | OpenCode/OhMy | WhereCode | Overlap | Decision |
| --- | --- | --- | --- | --- |
| Interactive coding execution loop | strong (`run`, session, TUI/web) | has action-layer runtime | high | delegate to OpenCode/OhMy |
| Multi-agent presets and model orchestration | strong (OhMy agents/categories) | basic role mapping | high | use OhMy as execution persona layer |
| MCP/plugin lifecycle | strong (`opencode mcp`, plugin loading) | partial local wrapping | high | delegate runtime management |
| Session export/import/history | strong (`export/import/session/db`) | partial run-state tracking | high | delegate session internals |
| GitHub/PR workflow hooks | built-in (`github`, `pr`) | not core | high | delegate |
| Tool sandbox/permission profiles | built-in agent policy model | partial custom policy | medium | keep WhereCode policy overlay only |
| Role routing | available via `--agent` + plugin | strong registry/routing files | medium | keep as control-plane routing contract |
| Requirement clarification (ask-first/no-guess) | weak/general | explicit planned gate | low | keep and implement in WhereCode |
| SDD stage gate (`intent->...->accept`) | weak/general | planned core value | low | keep and implement in WhereCode |
| Acceptance gate + evidence package | weak/general | planned core value | low | keep and implement in WhereCode |
| Remote progress API for mobile visibility | weak/general | planned API layer | low | keep and implement in WhereCode |
| Plan autopilot over project PLAN | weak/general | strong local script baseline | low | keep, but execute through adapters |

## 3. Quantified Overlap

- capability groups assessed: `12`
- high overlap: `5`
- medium overlap: `2`
- low overlap: `5`
- weighted overlap score: `50%`  
  (high=1.0, medium=0.5, low=0.0)

Interpretation:

- WhereCode currently has about half of its surface overlapping with OpenCode/OhMy execution/runtime concerns.
- V3 should explicitly remove duplicated execution responsibilities.

## 4. Boundary Decision (V3)

WhereCode should own:

1. requirement understanding + clarification gate
2. SDD workflow orchestration and artifact gate
3. acceptance/done gate with evidence requirements
4. role routing policy and context isolation policy
5. run timeline/report APIs (device-agnostic visibility)

WhereCode should delegate:

1. code execution/edit loop
2. agent runtime personalities and model bundles
3. plugin/MCP runtime operations
4. session internals and conversation history mechanics

## 5. De-dup Targets

1. downgrade `action_layer` to pure execution gateway adapter
2. remove/retire duplicated V2 execution scripts (`v2-*`, subproject cycle wrappers) from primary path
3. keep `stationctl` as orchestration entry, but route execution to OpenCode/OhMy adapter

## 6. Replan Trigger

This audit is the input baseline for:

- `PLAN.md` sprint reorder
- `docs/V3_PROJECT_PLAN.md` milestone update (integration-first)

