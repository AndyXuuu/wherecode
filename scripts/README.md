# Scripts (V3)

## Primary Entry

- `stationctl.sh`
  - service ops: `install|dev|start|stop|status`
  - orchestration: `main-orchestrate|plan-autopilot|orchestrate-policy`
  - checks: `check quick|dev|release|ops|main`

## Main Flow

- `main_orchestrate.sh`
  - V3 control-plane orchestration entry
  - executes requirement -> decomposition -> execution -> report flow

- `plan_autopilot.sh`
  - executes `PLAN.md` current sprint continuously
  - marks task status and writes operation logs

## Check Entry

- `check_all.sh`
  - API gateway (`POST /ops/checks/runs`)
  - primary scope for V3 release gate: `main`

- `check_all_local.sh`
  - local executor for check API
  - V3 main flow validation entry: `main`
