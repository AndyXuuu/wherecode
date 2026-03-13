# WhereCode V3 Engineering Directory Layout

Updated: 2026-03-12

## 1. Objective

Define a stable engineering layout so OpenCode / OhMyOpenCode can be updated independently without breaking WhereCode control-plane contracts.

## 2. Layer Boundaries

- `control_center/`: control-plane runtime, workflow state, gates, APIs.
- `action_layer/`: thin execution gateway (dispatch + normalized result only).
- `control_center/executors/`: stable adapter layer (owned by WhereCode).
- `.agents/`: role rules, skills, policies, MCP extension assets.
- `external/executors/`: upstream/fork source workspaces (not committed business code).
- `project/`: generated subprojects and requirement-driven outputs.
- `docs/`: architecture, plans, reports, and acceptance evidence.

## 3. V3 Directory Tree (Baseline)

```text
wherecode/
├─ .agents/
│  ├─ roles/
│  │  ├─ <role>/
│  │  │  └─ AGENTS.md
│  │  └─ README.md
│  ├─ skills/
│  ├─ policies/
│  └─ mcp/
├─ control_center/
│  ├─ executors/
│  │  ├─ contracts/
│  │  │  └─ README.md
│  │  ├─ registry/
│  │  │  └─ executors.json
│  │  ├─ adapters/
│  │  │  ├─ opencode/
│  │  │  │  └─ README.md
│  │  │  └─ ohmyopencode/
│  │  │     └─ README.md
│  │  └─ README.md
│  └─ ...
├─ external/
│  └─ executors/
│     ├─ README.md
│     ├─ .gitkeep
│     ├─ opencode/        # local clone/worktree (gitignored)
│     └─ ohmyopencode/    # local clone/worktree (gitignored)
├─ project/
│  ├─ requirements/
│  └─ <generated-subprojects>/
└─ docs/
   ├─ V3_PROJECT_PLAN.md
   └─ V3_ENGINEERING_LAYOUT.md
```

## 4. Update Strategy (OpenCode / OhMyOpenCode)

1. Keep external executor source out of main repo history:
   - clone/fork under `external/executors/<name>/`
   - ignore these folders in git
2. Keep adapter contracts stable in main repo:
   - request/response schema and error contract live in `control_center/executors/contracts/`
   - adapters convert external executor output to unified result schema
3. Upgrade by compatibility matrix:
   - register executor metadata in `control_center/executors/registry/executors.json`
   - each executor records tested commit/tag and compatibility notes
4. Do not let external source leak into control-plane:
   - no direct import from `external/executors/*` in core API modules
   - all invocation goes through adapter boundary
5. Keep role-profile source of truth stable:
   - canonical path: `.agents/roles/<role>/AGENTS.md`
   - legacy path `action_layer/agents/<role>/AGENTS.md` is compatibility only

## 5. Rules

- Main repo owns orchestration and quality gates only.
- External executors can be replaced/upgraded without changing orchestration contract.
- Any new executor must add:
  - adapter directory
  - registry entry
  - contract validation evidence
- Any new role must add:
  - `.agents/roles/<role>/AGENTS.md`
  - routing entry in `.agents/policies/role_routing.v3.json`
