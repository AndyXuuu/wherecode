# Executor Integration Plane (V3)

Purpose: keep a stable adapter boundary between WhereCode control-plane and external executors (OpenCode / OhMyOpenCode / others).

- `contracts/`: unified execute contract and error/result schema references.
- `registry/`: executor registration metadata and compatibility lock.
- `adapters/`: per-executor adapter implementations.

External source code is not stored here. Use `external/executors/<name>/` workspaces.

