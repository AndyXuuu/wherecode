#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PYTHON="${ROOT_DIR}/control_center/.venv/bin/python"
SCOPE="${1:-quick}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/check_backend.sh [scope]

Scopes:
  quick     core workflow/unit checks for daily iteration (default)
  full      full main-backend pytest suite (`tests/` only)
EOF
}

if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  echo "missing backend venv: ${BACKEND_PYTHON}"
  echo "create it first:"
  echo "  python3 -m venv control_center/.venv"
  echo "  control_center/.venv/bin/pip install -r control_center/requirements.txt"
  exit 1
fi

run_quick() {
  local -a quick_tests=(
    "tests/unit/test_v3_workflow_engine_api.py"
    "tests/unit/test_action_layer_llm_executor.py"
    "tests/unit/test_openapi_contract.py"
  )
  "${BACKEND_PYTHON}" -m pytest -q "${quick_tests[@]}"
}

run_full() {
  "${BACKEND_PYTHON}" -m pytest -q tests
}

case "${SCOPE}" in
  quick)
    run_quick
    ;;
  full)
    run_full
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "unknown scope: ${SCOPE}"
    usage
    exit 1
    ;;
esac
