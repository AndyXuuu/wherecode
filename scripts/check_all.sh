#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PYTHON="${ROOT_DIR}/control_center/.venv/bin/python"

if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  echo "missing backend venv: ${BACKEND_PYTHON}"
  echo "create it first:"
  echo "  python3 -m venv control_center/.venv"
  echo "  control_center/.venv/bin/pip install -r control_center/requirements.txt"
  exit 1
fi

echo "[1/2] backend tests"
"${BACKEND_PYTHON}" -m pytest -q

echo "[2/2] command center build (pnpm)"
pnpm --dir "${ROOT_DIR}/command_center" build

echo "all checks passed"
