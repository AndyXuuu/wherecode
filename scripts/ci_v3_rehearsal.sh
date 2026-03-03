#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_URL="${1:-http://127.0.0.1:8000}"
ACTION_URL="${2:-http://127.0.0.1:8100}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
PROBE_RUN_COUNT="${CI_PROBE_RUN_COUNT:-4}"
PROBE_WORKERS="${CI_PROBE_WORKERS:-2}"
RECOVERY_URL="${CI_RECOVERY_URL:-http://127.0.0.1:18080}"
RECOVERY_SQLITE_PATH="${CI_RECOVERY_SQLITE_PATH:-${ROOT_DIR}/.wherecode/ci-recovery/state.db}"
STARTED_CONTROL_CENTER=0
STARTED_ACTION_LAYER=0

wait_http_ok() {
  local url="$1"
  local max_try="${2:-45}"
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

service_running() {
  local target="$1"
  bash "${ROOT_DIR}/scripts/stationctl.sh" status "${target}" | grep -q "^${target}: running"
}

cleanup() {
  if [[ "${STARTED_CONTROL_CENTER}" -eq 1 ]]; then
    bash "${ROOT_DIR}/scripts/stationctl.sh" stop control-center >/dev/null 2>&1 || true
  fi
  if [[ "${STARTED_ACTION_LAYER}" -eq 1 ]]; then
    bash "${ROOT_DIR}/scripts/stationctl.sh" stop action-layer >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

export WHERECODE_TOKEN="${AUTH_TOKEN}"
export WHERECODE_RELOAD=false

echo "[1/8] ensure action-layer is running"
if ! service_running "action-layer"; then
  bash "${ROOT_DIR}/scripts/stationctl.sh" start action-layer
  STARTED_ACTION_LAYER=1
fi
wait_http_ok "${ACTION_URL}/healthz" 45

echo "[2/8] ensure control-center is running"
if ! service_running "control-center"; then
  bash "${ROOT_DIR}/scripts/stationctl.sh" start control-center
  STARTED_CONTROL_CENTER=1
fi
wait_http_ok "${CONTROL_URL}/healthz" 45
wait_http_ok "${CONTROL_URL}/action-layer/health" 45 "X-WhereCode-Token: ${AUTH_TOKEN}"

echo "[3/8] run HTTP async smoke"
WHERECODE_TOKEN="${AUTH_TOKEN}" bash "${ROOT_DIR}/scripts/http_async_smoke.sh" "${CONTROL_URL}"

echo "[4/8] run action-layer smoke"
bash "${ROOT_DIR}/scripts/action_layer_smoke.sh" "${ACTION_URL}"

echo "[5/8] run v3 workflow smoke"
WHERECODE_TOKEN="${AUTH_TOKEN}" bash "${ROOT_DIR}/scripts/v3_workflow_smoke.sh" "${CONTROL_URL}"

echo "[6/8] run v3 parallel probe"
WHERECODE_TOKEN="${AUTH_TOKEN}" \
PROBE_STRICT=true \
bash "${ROOT_DIR}/scripts/v3_parallel_probe.sh" "${CONTROL_URL}" "${PROBE_RUN_COUNT}" "${PROBE_WORKERS}"

echo "[7/8] run v3 recovery drill"
WHERECODE_TOKEN="${AUTH_TOKEN}" \
WHERECODE_SQLITE_PATH="${RECOVERY_SQLITE_PATH}" \
bash "${ROOT_DIR}/scripts/v3_recovery_drill.sh" "${RECOVERY_URL}" "${ACTION_URL}"

echo "[8/8] rehearsal summary"
echo "ci rehearsal passed: control=${CONTROL_URL} action=${ACTION_URL} probe_runs=${PROBE_RUN_COUNT}"
