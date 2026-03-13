# Agents Workspace (V3)

Canonical extension structure:

- `roles/`: per-role rules (`<role>/AGENTS.md`).
- `skills/`: reusable execution skills.
- `policies/`: routing and context isolation policies.
- `mcp/`: local MCP integration configs and manifests.

Rules:

- Role profile source of truth is `.agents/roles`.
- `action_layer/agents` is legacy compatibility path only.
- Every role reads only its own profile file.

