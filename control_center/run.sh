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

HOST="${WHERECODE_HOST:-0.0.0.0}"
PORT="${WHERECODE_PORT:-8000}"
RELOAD="${WHERECODE_RELOAD:-true}"

if [[ -f "${SCRIPT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${SCRIPT_DIR}/.env"
  set +a
fi

if [[ "${RELOAD}" == "true" ]]; then
  RELOAD_FLAG="--reload"
else
  RELOAD_FLAG=""
fi

cd "${REPO_ROOT}"
"${PYTHON_BIN}" -m uvicorn control_center.main:app --host "${HOST}" --port "${PORT}" ${RELOAD_FLAG}
