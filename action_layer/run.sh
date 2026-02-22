#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

if [[ -x "${VENV_PYTHON}" ]]; then
  PYTHON_BIN="${VENV_PYTHON}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if [[ -f "${SCRIPT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${SCRIPT_DIR}/.env"
  set +a
fi

cd "${REPO_ROOT}"
"${PYTHON_BIN}" -m action_layer.runtime
