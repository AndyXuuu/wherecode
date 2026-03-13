#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/check_all_local.sh [scope]

Scopes:
  quick      backend quick checks (default)
  dev        alias of quick
  release    backend full + command_center + project checks
  ops        go5 ops checkpoint (default profile quick)
  main       main-project orchestrate entry dry-run
  all        alias of release (legacy)
  backend    backend full tests only
  backend-quick backend quick checks only
  backend-full  backend full tests only
  llm-check  action-layer llm check only
  frontend   command_center build only
  projects   standalone project checks only
EOF
}

run_project_checks() {
  local project_dir="${ROOT_DIR}/project"
  local found=0
  if [[ ! -d "${project_dir}" ]]; then
    echo "[projects] no project directory, skip"
    return
  fi
  while IFS= read -r check_script; do
    found=1
    local rel_path="${check_script#${ROOT_DIR}/}"
    echo "[projects] ${rel_path}"
    bash "${check_script}"
  done < <(find "${project_dir}" -mindepth 2 -maxdepth 4 -type f -path "*/scripts/check.sh" | sort)
  if [[ "${found}" -eq 0 ]]; then
    echo "[projects] no scripts/check.sh found, skip"
  fi
}

run_llm_check_gate() {
  local action_layer_url="${CHECK_ALL_ACTION_LAYER_URL:-http://127.0.0.1:8100}"
  local role="${CHECK_ALL_LLM_ROLE:-module-dev}"
  local module_key="${CHECK_ALL_LLM_MODULE_KEY:-check_all/llm_check}"
  local text="${CHECK_ALL_LLM_TEXT:-run check_all llm check and return short summary}"
  bash "${ROOT_DIR}/scripts/action_layer_llm_check.sh" \
    "${action_layer_url}" \
    "${role}" \
    "${module_key}" \
    "${text}"
}

run_quick_checks() {
  echo "[1/1] backend quick checks"
  bash "${ROOT_DIR}/scripts/check_backend.sh" quick
}

run_backend_full_checks() {
  echo "[1/1] backend full tests"
  bash "${ROOT_DIR}/scripts/check_backend.sh" full
}

SCOPE="${1:-quick}"
case "${SCOPE}" in
  quick|dev)
    run_quick_checks
    ;;
  release|all)
    echo "[1/4] backend full baseline"
    run_backend_full_checks
    echo "[2/4] command-center build (pnpm)"
    bash "${ROOT_DIR}/scripts/check_command_center.sh"
    echo "[3/4] standalone project checks"
    run_project_checks
    echo "[4/4] release baseline done"
    ;;
  ops)
    local_profile="${CHECK_ALL_OPS_PROFILE:-quick}"
    echo "[ops] go5 ops checkpoint (profile=${local_profile})"
    bash "${ROOT_DIR}/scripts/go5_ops_checkpoint.sh" "${local_profile}"
    ;;
  main)
    echo "[1/2] backend quick checks"
    run_quick_checks
    echo "[2/2] main-project orchestrate entry dry-run"
    bash "${ROOT_DIR}/scripts/main_orchestrate.sh" --dry-run
    ;;
  backend)
    echo "[backend] full tests"
    bash "${ROOT_DIR}/scripts/check_backend.sh" full
    ;;
  backend-quick)
    echo "[backend-quick] quick checks"
    bash "${ROOT_DIR}/scripts/check_backend.sh" quick
    ;;
  backend-full)
    echo "[backend-full] full tests"
    bash "${ROOT_DIR}/scripts/check_backend.sh" full
    ;;
  llm-check)
    echo "[llm-check] action-layer llm check"
    run_llm_check_gate
    ;;
  frontend)
    echo "[frontend] command center build (pnpm)"
    bash "${ROOT_DIR}/scripts/check_command_center.sh"
    ;;
  projects)
    echo "[projects] standalone project checks"
    run_project_checks
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "unknown scope: ${SCOPE}"
    usage
    exit 1
    ;;
esac

echo "checks passed (scope=${SCOPE})"
