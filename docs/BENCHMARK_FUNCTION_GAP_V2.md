# Benchmark Function Gap V2

Updated: 2026-03-11

## Scope

Function-level gap check between:
- OpenCode
- Oh My OpenCode
- OpenClaw
- WhereCode (current repo)

Status labels:
- `implemented`
- `partial`
- `missing`

## Matrix

| Capability | Benchmark evidence | WhereCode status | Local evidence | Gap / Priority |
| --- | --- | --- | --- | --- |
| Role-based agents + subagents | OpenCode docs define primary agents/subagents and per-agent options; Oh My OpenCode emphasizes specialized agents/workflows. | `implemented` | `control_center/capabilities/agent_rules_registry.json`; `action_layer/agents/*/AGENTS.md` (compat: `agent.md`); `control_center/services/dev_routing_matrix.py` | Need richer role taxonomy by stack/language packs. `P1` |
| Plan/build style execution modes | OpenCode docs expose built-in agents (`build`, `plan`, etc.); Oh My OpenCode has mode-driven workflows. | `implemented` | `scripts/v2_run.sh`; `docs/OPERATIONS_V2.md`; `docs/v2_reports/latest_stock-sentiment_v2_run.json` | Keep compatible CLI UX, no blocker. `P2` |
| Agent rule files and precedence model | OpenCode rules support project/global `AGENTS.md`, precedence, `opencode.json` instruction files (including URLs). | `partial` | `action_layer/services/agent_profile_loader.py`; `control_center/api/agent_rules_routes.py` | Missing hierarchical rule precedence + external instruction include pipeline. `P1` |
| Context isolation + memory namespaces | OpenCode/OpenClaw document session/context models; OpenClaw exposes memory/tooling concepts. | `partial` | `control_center/services/context_memory_store.py`; `control_center/api/context_memory_routes.py` | Has `shared/project/run` KV memory, but lacks richer memory policies (semantic recall/compaction plugins). `P1` |
| MCP/tool protocol integration | OpenCode has MCP server docs; OpenClaw docs include MCP/tool sections. | `partial` | `control_center/capabilities/templates/mcp.manifest.json`; `control_center/capabilities/capability_contract.schema.json` | Contract exists, runtime MCP server lifecycle/bridge is not implemented end-to-end. `P0` |
| Hooks / plugin ecosystem | OpenClaw docs describe hooks/integrations; OpenCode has plugin docs. | `missing` | `control_center/capabilities/registry.json` (empty packages) | No general hook bus/plugin runtime + no plugin SDK flow. `P0` |
| Channel/integration surface | OpenClaw highlights multi-channel integrations. | `missing` | N/A in control-center/action-layer APIs | No first-class channel adapters in main runtime. `P1` |
| Remote/headless operation + observability | OpenCode server docs describe remote control endpoints; OpenClaw has remote/onboarding docs. | `partial` | `control_center/api/ops_check_routes.py`; `control_center/api/v2_report_routes.py`; `docs/OPERATIONS_V2.md` | Has API polling/reporting, missing unified event stream/webhook push model. `P0` |
| Capability registry/package lifecycle | OpenClaw exposes skills registry; OpenCode has plugin ecosystem docs. | `partial` | `control_center/capabilities/registry.json`; `scripts/capability_contract_check.py` | Registry/check exists but package install/enable/disable lifecycle is not complete. `P0` |
| Safety/approval boundaries | Benchmarks expose permission/sandbox concepts. | `implemented` | `action_layer/services/agent_profile_loader.py`; `docs/OPERATIONS_V2.md` clarification gate + confirmation fields | Extend to policy-as-code for capability-level permissions. `P1` |

## Alignment Backlog (Next)

1. `P0` MCP runtime adapter: register/start/health/retry MCP packages from capability registry.
2. `P0` Hook/event bus: emit workflow/action events and support webhook/plugin subscribers.
3. `P0` Capability lifecycle: install/enable/disable/list package APIs and CLI.
4. `P0` Remote stream API: push run timeline via SSE/WebSocket in addition to polling.
5. `P1` Rule precedence engine: role rule merge (`global -> project -> role -> run`) with deterministic override.
6. `P1` Memory expansion: pluggable memory backends and retention/compaction policy.
7. `P1` Channel adapter layer: start from webhook/slack/telegram minimal connectors.

## Source Links

- OpenCode Agents: https://opencode.ai/docs/agents
- OpenCode Rules: https://opencode.ai/docs/rules
- OpenCode Plugins: https://opencode.ai/docs/plugins
- OpenCode Server: https://opencode.ai/docs/server
- OpenCode MCP servers: https://opencode.ai/docs/mcp-servers
- Oh My OpenCode Docs: https://ohmyopencode.com/docs
- Oh My OpenCode Site: https://ohmyopencode.com/
- OpenClaw channels intro: https://docs.openclaw.ai/core-concepts/channels/introduction
- OpenClaw skills registry intro: https://docs.openclaw.ai/core-concepts/skills-registry/introduction
- OpenClaw hooks intro: https://docs.openclaw.ai/core-concepts/integrations/hooks/introduction
- OpenClaw local onboarding: https://docs.openclaw.ai/core-concepts/onboarding/local
- OpenClaw remote onboarding: https://docs.openclaw.ai/core-concepts/onboarding/remote
