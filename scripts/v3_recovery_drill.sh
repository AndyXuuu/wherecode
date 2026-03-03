#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_HOST="${WHERECODE_RECOVERY_HOST:-127.0.0.1}"
CONTROL_PORT="${WHERECODE_RECOVERY_PORT:-18080}"
CONTROL_URL="${1:-http://${CONTROL_HOST}:${CONTROL_PORT}}"
ACTION_URL="${2:-http://127.0.0.1:8100}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
SQLITE_PATH="${WHERECODE_SQLITE_PATH:-${ROOT_DIR}/.wherecode/recovery-drill/state.db}"
CONTROL_PYTHON="${ROOT_DIR}/control_center/.venv/bin/python"
CONTROL_LOG="${ROOT_DIR}/.wherecode/run/recovery-control-center.log"
CONTROL_PID_FILE="${ROOT_DIR}/.wherecode/run/recovery-control-center.pid"
STARTED_ACTION_LAYER=0

if [[ ! -x "${CONTROL_PYTHON}" ]]; then
  CONTROL_PYTHON="${PYTHON_BIN:-python3}"
fi

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

start_action_layer_if_needed() {
  if curl -fsS "${ACTION_URL}/healthz" >/dev/null 2>&1; then
    return 0
  fi
  echo "starting action-layer for recovery drill"
  bash "${ROOT_DIR}/scripts/stationctl.sh" start action-layer >/dev/null
  STARTED_ACTION_LAYER=1
  wait_http_ok "${ACTION_URL}/healthz" 45
}

stop_action_layer_if_started() {
  if [[ "${STARTED_ACTION_LAYER}" -eq 1 ]]; then
    bash "${ROOT_DIR}/scripts/stationctl.sh" stop action-layer >/dev/null 2>&1 || true
  fi
}

start_control_center() {
  mkdir -p "$(dirname "${SQLITE_PATH}")"
  mkdir -p "$(dirname "${CONTROL_LOG}")"

  WHERECODE_STATE_BACKEND=sqlite \
  WHERECODE_SQLITE_PATH="${SQLITE_PATH}" \
  WHERECODE_TOKEN="${AUTH_TOKEN}" \
  WHERECODE_AUTH_ENABLED=true \
  WHERECODE_RELOAD=false \
  WHERECODE_HOST="${CONTROL_HOST}" \
  WHERECODE_PORT="${CONTROL_PORT}" \
  ACTION_LAYER_BASE_URL="${ACTION_URL}" \
  "${CONTROL_PYTHON}" -m uvicorn control_center.main:app \
    --host "${CONTROL_HOST}" \
    --port "${CONTROL_PORT}" \
    >"${CONTROL_LOG}" 2>&1 &

  local pid="$!"
  echo "${pid}" >"${CONTROL_PID_FILE}"
  wait_http_ok "${CONTROL_URL}/healthz" 45
}

stop_control_center() {
  if [[ ! -f "${CONTROL_PID_FILE}" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "${CONTROL_PID_FILE}")"
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    for _ in $(seq 1 30); do
      if ! kill -0 "${pid}" >/dev/null 2>&1; then
        break
      fi
      sleep 0.2
    done
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  fi
  rm -f "${CONTROL_PID_FILE}"
}

cleanup() {
  stop_control_center
  stop_action_layer_if_started
}

trap cleanup EXIT

header_auth=("X-WhereCode-Token: ${AUTH_TOKEN}")
header_json=("Content-Type: application/json" "X-WhereCode-Token: ${AUTH_TOKEN}")

echo "[1/8] prepare clean sqlite state"
rm -f "${SQLITE_PATH}"

echo "[2/8] ensure action-layer is available"
start_action_layer_if_needed

echo "[3/8] start isolated control-center (sqlite)"
start_control_center

echo "[4/8] create run and bootstrap workflow"
run_payload="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs" \
  -H "${header_json[0]}" \
  -H "${header_json[1]}" \
  -d '{"project_id":"proj_recovery_drill","requested_by":"ops-drill"}')"
run_id="$(printf '%s' "${run_payload}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/bootstrap" \
  -H "${header_json[0]}" \
  -H "${header_json[1]}" \
  -d '{"modules":["needs-discussion"]}' >/dev/null

echo "[5/8] execute workflow to terminal"
execute_payload="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/execute" \
  -H "${header_json[0]}" \
  -H "${header_json[1]}" \
  -d '{"max_loops":60}')"
execute_status="$(printf '%s' "${execute_payload}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_status"])')"

if [[ "${execute_status}" == "blocked" ]]; then
  discussion_id="$(printf '%s' "${execute_payload}" | python3 -c 'import json,sys; p=json.load(sys.stdin); ids=p.get("waiting_discussion_workitem_ids", []); print(ids[0] if ids else "")')"
  curl -fsS -X POST "${CONTROL_URL}/v3/workflows/workitems/${discussion_id}/discussion/resolve" \
    -H "${header_json[0]}" \
    -H "${header_json[1]}" \
    -d '{"decision":"choose option-a","resolved_by":"chief-architect"}' >/dev/null
  execute_payload="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/execute" \
    -H "${header_json[0]}" \
    -H "${header_json[1]}" \
    -d '{"max_loops":60}')"
  execute_status="$(printf '%s' "${execute_payload}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_status"])')"
fi

if [[ "${execute_status}" == "waiting_approval" ]]; then
  approval_id="$(printf '%s' "${execute_payload}" | python3 -c 'import json,sys; p=json.load(sys.stdin); ids=p.get("waiting_approval_workitem_ids", []); print(ids[0] if ids else "")')"
  curl -fsS -X POST "${CONTROL_URL}/v3/workflows/workitems/${approval_id}/approve" \
    -H "${header_json[0]}" \
    -H "${header_json[1]}" \
    -d '{"approved_by":"ops-owner"}' >/dev/null
  execute_payload="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/execute" \
    -H "${header_json[0]}" \
    -H "${header_json[1]}" \
    -d '{"max_loops":60}')"
  execute_status="$(printf '%s' "${execute_payload}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_status"])')"
fi

if [[ "${execute_status}" != "succeeded" ]]; then
  echo "recovery drill setup failed: run_status=${execute_status}"
  printf '%s\n' "${execute_payload}"
  exit 1
fi

echo "[6/8] record pre-restart gate/artifact counts"
gate_before="$(curl -fsS "${CONTROL_URL}/v3/workflows/runs/${run_id}/gates" -H "${header_auth[0]}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
artifact_before="$(curl -fsS "${CONTROL_URL}/v3/workflows/runs/${run_id}/artifacts" -H "${header_auth[0]}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"

echo "[7/8] restart control-center process"
stop_control_center
start_control_center

echo "[8/8] verify persisted run and counts after restart"
run_after="$(curl -fsS "${CONTROL_URL}/v3/workflows/runs/${run_id}" -H "${header_auth[0]}")"
status_after="$(printf '%s' "${run_after}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
gate_after="$(curl -fsS "${CONTROL_URL}/v3/workflows/runs/${run_id}/gates" -H "${header_auth[0]}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
artifact_after="$(curl -fsS "${CONTROL_URL}/v3/workflows/runs/${run_id}/artifacts" -H "${header_auth[0]}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"

if [[ "${status_after}" != "succeeded" ]]; then
  echo "recovery drill failed: restored run status=${status_after}"
  exit 1
fi
if [[ "${gate_after}" != "${gate_before}" ]]; then
  echo "recovery drill failed: gate count changed ${gate_before} -> ${gate_after}"
  exit 1
fi
if [[ "${artifact_after}" != "${artifact_before}" ]]; then
  echo "recovery drill failed: artifact count changed ${artifact_before} -> ${artifact_after}"
  exit 1
fi

echo "recovery drill passed: run_id=${run_id}, gates=${gate_after}, artifacts=${artifact_after}"
