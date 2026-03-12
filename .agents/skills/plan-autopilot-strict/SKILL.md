---
name: plan-autopilot-strict
description: Run PLAN.md tasks in release-gate mode with strict failure handling. Use when the user needs fail-stop behavior before release, with exactly one repair retry per failed task; optionally continue by skipping failed tasks after one retry.
---

# Plan Autopilot Strict

Run strict PLAN autopilot and return concise gate results.

## Run

Use repo root: `/Users/andyxu/Documents/project/wherecode`.

### Mode A: Fail-stop (default gate)
```bash
bash scripts/stationctl.sh plan-autopilot --strict --max-retries 2 --retry-interval 10
```
- Meaning:
  - One task attempt + one repair retry.
  - If still failed, stop immediately (gate red).

### Mode B: Skip-next (continue queue)
```bash
bash scripts/stationctl.sh plan-autopilot --non-strict --max-retries 2 --retry-interval 10
```
- Meaning:
  - One task attempt + one repair retry.
  - If still failed, mark blocker and continue to next task.

### Dry run
```bash
bash scripts/stationctl.sh --dry-run plan-autopilot --max-tasks 1
```

## Behavior
- Read `PLAN.md` current sprint table.
- Pick first `planned|doing` task.
- Run orchestration.
- On fail, retry once (`--max-retries 2`).
- Apply mode rule:
  - `--strict`: stop on exhausted retry.
  - `--non-strict`: continue to next task.

## Output
- Report mode used (`fail-stop` or `skip-next`).
- Report executed task count and latest task id/status.
- If failed, include summary path:
  - `docs/ops_reports/plan_autopilot/<task-slug>/latest.json`
