---
name: plan-autopilot
description: Execute PLAN.md current sprint tasks continuously with stationctl plan-autopilot until no planned/doing task remains. Use when the user asks for unattended plan execution, continuous sprint delivery, or "run until done" behavior while keeping project rules and plan status updates.
---

# Plan Autopilot

Run the repository autopilot command and return concise progress.

## Run
- Use repo root: `/Users/andyxu/Documents/project/wherecode`.
- Prefer:
```bash
bash scripts/stationctl.sh plan-autopilot
```
- Common controls:
```bash
# preview only
bash scripts/stationctl.sh --dry-run plan-autopilot --max-tasks 1

# limit batch size
bash scripts/stationctl.sh plan-autopilot --max-tasks 3

# retry forever for blocked task
bash scripts/stationctl.sh plan-autopilot --max-retries 0 --retry-interval 10
```

## Expected Behavior
- Read `PLAN.md` section `Current Sprint (Ordered)`.
- Pick first task with status `planned` or `doing`.
- Execute via main orchestration path.
- Update task status/log in `PLAN.md`.
- Continue until no `planned/doing` task left or max limit reached.

## Output
- Report executed task count.
- Report latest task id/status.
- If blocked, report summary path:
  - `docs/ops_reports/plan_autopilot/<task-slug>/latest.json`
