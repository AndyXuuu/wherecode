# Context Isolation Policy (V3)

## Goal

Reduce token usage and prevent cross-role leakage.

## Rules

1. Role profile read scope:
- Role can read only `.agents/roles/<self>/AGENTS.md` (or legacy equivalent).

2. Runtime context layers:
- `shared`: global immutable policies.
- `project`: project-level decisions and architecture.
- `run`: current execution chain state.
- `module`: module-local implementation/test context.

3. Read/write matrix:
- `chief-architect`: read `shared/project/run`, write `project/run`.
- `module-dev`: read `shared/project/module`, write `module`.
- `doc-manager`: read `shared/project/run`, write `project`.
- `qa-test`/`integration-test`: read `shared/project/module/run`, write `run`.
- `acceptance`/`release-manager`: read `shared/project/run`, write `run`.

4. Clarification gate:
- If requirement ambiguity is detected, set workflow status to `awaiting_clarification`.
- No implementation stage is allowed before clarification is resolved.

