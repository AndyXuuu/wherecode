#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export MB3_DRY_RUN_PROJECT_NAME="${MB3_DRY_RUN_PROJECT_NAME:-main-orchestrate-$(date -u +%Y%m%d%H%M%S)}"
export MB3_DRY_RUN_TASK_TITLE="${MB3_DRY_RUN_TASK_TITLE:-main project orchestration task}"
export MB3_DRY_RUN_REQUIREMENTS="${MB3_DRY_RUN_REQUIREMENTS:-build programmer-focused automation system with requirement decomposition, module execution, documentation sync, and acceptance checks}"
export MB3_DRY_RUN_MODULE_HINTS="${MB3_DRY_RUN_MODULE_HINTS:-requirements,decomposition,implementation,documentation,testing,release}"
export MB3_DRY_RUN_MAX_MODULES="${MB3_DRY_RUN_MAX_MODULES:-6}"
export MB3_DRY_RUN_STRATEGY="${MB3_DRY_RUN_STRATEGY:-balanced}"
export MB3_DRY_RUN_EXECUTE="${MB3_DRY_RUN_EXECUTE:-true}"
export MB3_DRY_RUN_FORCE_REDECOMPOSE="${MB3_DRY_RUN_FORCE_REDECOMPOSE:-false}"
export MB3_DRY_RUN_REQUESTED_BY="${MB3_DRY_RUN_REQUESTED_BY:-main-orchestrate}"
export MB3_DRY_RUN_CONFIRMED_BY="${MB3_DRY_RUN_CONFIRMED_BY:-owner}"
export MB3_DRY_RUN_COMMAND_PREFIX="${MB3_DRY_RUN_COMMAND_PREFIX:-/orchestrate}"
export MB3_DRY_RUN_REPORT_DIR="${MB3_DRY_RUN_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
export MB3_DRY_RUN_LATEST_SUMMARY_PATH="${MB3_DRY_RUN_LATEST_SUMMARY_PATH:-${ROOT_DIR}/docs/ops_reports/latest_main_orchestrate.json}"

normalized_args=()
for arg in "$@"; do
  if [[ "${arg}" == --*=* ]]; then
    normalized_args+=("${arg%%=*}")
    normalized_args+=("${arg#*=}")
  else
    normalized_args+=("${arg}")
  fi
done

if ((${#normalized_args[@]} > 0)); then
  bash "${ROOT_DIR}/scripts/mb3_dry_run_seed.sh" "${normalized_args[@]}"
else
  bash "${ROOT_DIR}/scripts/mb3_dry_run_seed.sh"
fi
