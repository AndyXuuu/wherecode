#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_URL="${1:-http://127.0.0.1:8000}"
ACTION_URL="${2:-http://127.0.0.1:8100}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"

wait_http_ok() {
  local url="$1"
  local max_try="${2:-30}"
  local header="${3:-}"

  for _ in $(seq 1 "${max_try}"); do
    if [[ -n "${header}" ]]; then
      if curl -fsS "${url}" -H "${header}" >/dev/null; then
        return 0
      fi
    else
      if curl -fsS "${url}" >/dev/null; then
        return 0
      fi
    fi
    sleep 1
  done

  echo "timeout waiting for ${url}"
  return 1
}

cleanup() {
  bash "${ROOT_DIR}/scripts/stationctl.sh" stop all >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "[1/6] start all services"
bash "${ROOT_DIR}/scripts/stationctl.sh" start all

echo "[2/6] wait control center health"
wait_http_ok "${CONTROL_URL}/healthz"

echo "[3/6] wait action layer health"
wait_http_ok "${ACTION_URL}/healthz"

echo "[4/6] wait control->action proxy health"
wait_http_ok "${CONTROL_URL}/action-layer/health" 30 "X-WhereCode-Token: ${AUTH_TOKEN}"

echo "[5/6] run control async smoke"
WHERECODE_TOKEN="${AUTH_TOKEN}" bash "${ROOT_DIR}/scripts/http_async_smoke.sh" "${CONTROL_URL}"

echo "[6/6] run action layer smoke"
bash "${ROOT_DIR}/scripts/action_layer_smoke.sh" "${ACTION_URL}"

echo "full stack smoke passed"
