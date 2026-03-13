# External Executors Workspace

This directory stores local upstream/fork checkouts for external executors.

Examples:
- `external/executors/opencode/`
- `external/executors/ohmyopencode/`

Policy:
- treat as disposable local workspace
- do not commit external source code into WhereCode main repository
- upgrades happen by pulling/rebasing in each external checkout, then validating adapter compatibility

