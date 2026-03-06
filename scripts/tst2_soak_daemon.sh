#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.wherecode/run"
PID_FILE="${RUN_DIR}/tst2-soak.pid"
COMPAT_PID_FILE="${RUN_DIR}/tst2-soak-24h.pid"
LOG_FILE="${RUN_DIR}/tst2-soak.log"
START_FILE="${RUN_DIR}/tst2-soak.start"

CONTROL_URL="${TST2_SOAK_CONTROL_URL:-http://127.0.0.1:8000}"
ACTION_URL="${TST2_SOAK_ACTION_URL:-http://127.0.0.1:8100}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
SOAK_DURATION_SECONDS="${TST2_SOAK_DURATION_SECONDS:-86400}"
SOAK_INTERVAL_SECONDS="${TST2_SOAK_INTERVAL_SECONDS:-300}"
SOAK_PROBE_RUN_COUNT="${TST2_SOAK_PROBE_RUN_COUNT:-2}"
SOAK_PROBE_WORKERS="${TST2_SOAK_PROBE_WORKERS:-1}"
SOAK_RUN_PROBE_EACH_ROUND="${TST2_SOAK_RUN_PROBE_EACH_ROUND:-true}"
SOAK_SKIP_SERVICE_START="${TST2_SOAK_SKIP_SERVICE_START:-false}"
SOAK_FAIL_ON_FAILED_DELTA="${TST2_SOAK_FAIL_ON_FAILED_DELTA:-true}"
SOAK_MAX_FAILED_RUN_DELTA="${TST2_SOAK_MAX_FAILED_RUN_DELTA:-0}"
SOAK_REPORT_DIR="${TST2_SOAK_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"

STRICT_MODE=false
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_soak_daemon.sh <start|status|stop|restart> [options]

Options:
  --strict                      status mode exits non-zero on stale/failed guard
  --dry-run                     print actions only
  --control-url <url>           default: http://127.0.0.1:8000
  --action-url <url>            default: http://127.0.0.1:8100
  --token <token>               default: WHERECODE_TOKEN or change-me
  --duration <seconds>          default: 86400
  --interval <seconds>          default: 300
  --probe-runs <count>          default: 2
  --probe-workers <count>       default: 1
  --probe-each-round <bool>     default: true
  --skip-service-start <bool>   default: false
  --fail-on-failed-delta <bool> default: true
  --max-failed-run-delta <n>    default: 0
  --report-dir <path>           default: docs/ops_reports

Examples:
  bash scripts/tst2_soak_daemon.sh start
  bash scripts/tst2_soak_daemon.sh status --strict
  bash scripts/tst2_soak_daemon.sh stop
  bash scripts/tst2_soak_daemon.sh restart --duration 3600 --interval 120
EOF
}

is_pid_running() {
  local pid="$1"
  if [[ -z "${pid}" ]]; then
    return 1
  fi
  python3 - "${pid}" <<'PY'
from __future__ import annotations

import os
import sys

pid = int(sys.argv[1])
try:
    os.kill(pid, 0)
except ProcessLookupError:
    raise SystemExit(1)
except PermissionError:
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
raise SystemExit(0)
PY
}

count_sample_lines() {
  local samples_file="$1"
  if [[ ! -f "${samples_file}" ]]; then
    echo "0"
    return 0
  fi
  awk 'NF {count++} END {print count+0}' "${samples_file}"
}

cleanup_stale_pid() {
  for pidf in "${PID_FILE}" "${COMPAT_PID_FILE}"; do
    if [[ ! -f "${pidf}" ]]; then
      continue
    fi
    pid="$(cat "${pidf}")"
    if is_pid_running "${pid}"; then
      continue
    fi
    rm -f "${pidf}"
  done
}

find_running_pid() {
  for pidf in "${PID_FILE}" "${COMPAT_PID_FILE}"; do
    if [[ ! -f "${pidf}" ]]; then
      continue
    fi
    pid="$(cat "${pidf}")"
    if is_pid_running "${pid}"; then
      echo "${pid}|${pidf}"
      return 0
    fi
  done
  return 1
}

has_fresh_soak_activity() {
  set +e
  raw_status="$(bash "${ROOT_DIR}/scripts/tst2_soak_status.sh" 2>/dev/null)"
  status_rc=$?
  set -e
  if [[ "${status_rc}" -ne 0 ]]; then
    return 1
  fi

  python3 - "${raw_status}" <<'PY'
from __future__ import annotations

import json
import sys

try:
    payload = json.loads(sys.argv[1])
except Exception:  # noqa: BLE001
    raise SystemExit(1)

if not isinstance(payload, dict):
    raise SystemExit(1)

if payload.get("error"):
    raise SystemExit(1)

stale = bool(payload.get("stale"))
age = int(payload.get("last_sample_age_seconds", 10**9))
max_staleness = int(payload.get("max_staleness_seconds", 0))

if not stale and age <= max_staleness:
    raise SystemExit(0)
raise SystemExit(1)
PY
}

print_start_command() {
  cat <<EOF
env SOAK_DURATION_SECONDS=${SOAK_DURATION_SECONDS} \
SOAK_INTERVAL_SECONDS=${SOAK_INTERVAL_SECONDS} \
SOAK_PROBE_RUN_COUNT=${SOAK_PROBE_RUN_COUNT} \
SOAK_PROBE_WORKERS=${SOAK_PROBE_WORKERS} \
SOAK_RUN_PROBE_EACH_ROUND=${SOAK_RUN_PROBE_EACH_ROUND} \
SOAK_SKIP_SERVICE_START=${SOAK_SKIP_SERVICE_START} \
SOAK_FAIL_ON_FAILED_DELTA=${SOAK_FAIL_ON_FAILED_DELTA} \
SOAK_MAX_FAILED_RUN_DELTA=${SOAK_MAX_FAILED_RUN_DELTA} \
WHERECODE_TOKEN=${AUTH_TOKEN} \
bash scripts/tst2_soak.sh ${CONTROL_URL} ${ACTION_URL}
EOF
}

start_daemon() {
  cleanup_stale_pid

  if running_info="$(find_running_pid)"; then
    existing_pid="${running_info%%|*}"
    existing_pid_file="${running_info#*|}"
    if [[ "${existing_pid_file}" != "${PID_FILE}" ]]; then
      echo "${existing_pid}" >"${PID_FILE}"
    fi
    echo "tst2 soak already running (pid=${existing_pid}, pid_file=${existing_pid_file})"
    return 0
  fi
  if has_fresh_soak_activity; then
    echo "tst2 soak appears active by fresh samples (pid file unavailable); skip new start to avoid duplicate writers"
    return 0
  fi

  mkdir -p "${RUN_DIR}"
  mkdir -p "${SOAK_REPORT_DIR}"
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[dry-run] nohup $(print_start_command) > ${LOG_FILE} 2>&1 &"
    return 0
  fi

  local total_rounds=$(( (SOAK_DURATION_SECONDS + SOAK_INTERVAL_SECONDS - 1) / SOAK_INTERVAL_SECONDS ))
  if [[ "${total_rounds}" -lt 1 ]]; then
    total_rounds=1
  fi

  local resume_samples_path=""
  local resume_probe_log_path=""
  local resume_summary_path=""
  local resume_existing_rounds=0
  local candidate_samples_path=""
  local candidate_existing_rounds=0
  for candidate_samples_path in "${SOAK_REPORT_DIR}"/*-tst2-soak-samples.jsonl; do
    [[ -e "${candidate_samples_path}" ]] || continue
    candidate_existing_rounds="$(count_sample_lines "${candidate_samples_path}")"
    if [[ "${candidate_existing_rounds}" -le 0 || "${candidate_existing_rounds}" -ge "${total_rounds}" ]]; then
      continue
    fi
    if [[ -z "${resume_samples_path}" ]]; then
      resume_samples_path="${candidate_samples_path}"
      resume_existing_rounds="${candidate_existing_rounds}"
      continue
    fi
    if [[ "${candidate_existing_rounds}" -gt "${resume_existing_rounds}" ]]; then
      resume_samples_path="${candidate_samples_path}"
      resume_existing_rounds="${candidate_existing_rounds}"
      continue
    fi
    if [[ "${candidate_existing_rounds}" -eq "${resume_existing_rounds}" && "${candidate_samples_path}" -nt "${resume_samples_path}" ]]; then
      resume_samples_path="${candidate_samples_path}"
      resume_existing_rounds="${candidate_existing_rounds}"
    fi
  done

  if [[ -n "${resume_samples_path}" ]]; then
    local resume_prefix
    resume_prefix="${resume_samples_path%-tst2-soak-samples.jsonl}"
    resume_probe_log_path="${resume_prefix}-tst2-soak-probe.log"
    resume_summary_path="${resume_prefix}-tst2-soak-summary.md"
  fi

  local -a soak_cmd=(
    env
    "SOAK_DURATION_SECONDS=${SOAK_DURATION_SECONDS}"
    "SOAK_INTERVAL_SECONDS=${SOAK_INTERVAL_SECONDS}"
    "SOAK_PROBE_RUN_COUNT=${SOAK_PROBE_RUN_COUNT}"
    "SOAK_PROBE_WORKERS=${SOAK_PROBE_WORKERS}"
    "SOAK_RUN_PROBE_EACH_ROUND=${SOAK_RUN_PROBE_EACH_ROUND}"
    "SOAK_SKIP_SERVICE_START=${SOAK_SKIP_SERVICE_START}"
    "SOAK_FAIL_ON_FAILED_DELTA=${SOAK_FAIL_ON_FAILED_DELTA}"
    "SOAK_MAX_FAILED_RUN_DELTA=${SOAK_MAX_FAILED_RUN_DELTA}"
    "SOAK_REPORT_DIR=${SOAK_REPORT_DIR}"
    "WHERECODE_TOKEN=${AUTH_TOKEN}"
    bash
    "${ROOT_DIR}/scripts/tst2_soak.sh"
    "${CONTROL_URL}"
    "${ACTION_URL}"
  )

  if [[ -n "${resume_samples_path}" ]]; then
    soak_cmd=(
      env
      "SOAK_DURATION_SECONDS=${SOAK_DURATION_SECONDS}"
      "SOAK_INTERVAL_SECONDS=${SOAK_INTERVAL_SECONDS}"
      "SOAK_PROBE_RUN_COUNT=${SOAK_PROBE_RUN_COUNT}"
      "SOAK_PROBE_WORKERS=${SOAK_PROBE_WORKERS}"
      "SOAK_RUN_PROBE_EACH_ROUND=${SOAK_RUN_PROBE_EACH_ROUND}"
      "SOAK_SKIP_SERVICE_START=${SOAK_SKIP_SERVICE_START}"
      "SOAK_FAIL_ON_FAILED_DELTA=${SOAK_FAIL_ON_FAILED_DELTA}"
      "SOAK_MAX_FAILED_RUN_DELTA=${SOAK_MAX_FAILED_RUN_DELTA}"
      "SOAK_REPORT_DIR=${SOAK_REPORT_DIR}"
      "SOAK_SAMPLES_PATH=${resume_samples_path}"
      "SOAK_PROBE_LOG_PATH=${resume_probe_log_path}"
      "SOAK_SUMMARY_PATH=${resume_summary_path}"
      "WHERECODE_TOKEN=${AUTH_TOKEN}"
      bash
      "${ROOT_DIR}/scripts/tst2_soak.sh"
      "${CONTROL_URL}"
      "${ACTION_URL}"
    )
  fi

  local launch_mode="nohup"
  local pid=""
  if command -v setsid >/dev/null 2>&1; then
    launch_mode="setsid"
    nohup setsid "${soak_cmd[@]}" >"${LOG_FILE}" 2>&1 < /dev/null &
    pid="$!"
  elif command -v python3 >/dev/null 2>&1; then
    launch_mode="python3-start_new_session"
    pid="$(
      python3 - "${LOG_FILE}" "${soak_cmd[@]}" <<'PY'
from __future__ import annotations

import os
import subprocess
import sys

log_path = sys.argv[1]
cmd = sys.argv[2:]
if not cmd:
    raise SystemExit("missing command")

with open(log_path, "ab", buffering=0) as log_fh, open(os.devnull, "rb", buffering=0) as null_in:
    proc = subprocess.Popen(
        cmd,
        stdin=null_in,
        stdout=log_fh,
        stderr=log_fh,
        start_new_session=True,
        close_fds=True,
    )
print(proc.pid)
PY
    )"
  else
    nohup "${soak_cmd[@]}" >"${LOG_FILE}" 2>&1 < /dev/null &
    pid="$!"
  fi

  if [[ -z "${pid}" ]]; then
    echo "tst2 soak failed: no pid returned"
    return 1
  fi
  echo "${pid}" >"${PID_FILE}"
  date -u +"%Y-%m-%dT%H:%M:%SZ control=${CONTROL_URL} action=${ACTION_URL} launch=${launch_mode} resume_rounds=${resume_existing_rounds} resume_samples=${resume_samples_path:-none}" >"${START_FILE}"
  sleep 2
  if ! is_pid_running "${pid}"; then
    rm -f "${PID_FILE}"
    echo "tst2 soak failed to stay running"
    echo "log: ${LOG_FILE}"
    tail -n 20 "${LOG_FILE}" || true
    return 1
  fi
  echo "tst2 soak started (pid=${pid}, launch=${launch_mode})"
  if [[ -n "${resume_samples_path}" ]]; then
    echo "tst2 soak resumed from existing samples: ${resume_samples_path} (rounds=${resume_existing_rounds}/${total_rounds})"
  fi
  echo "log: ${LOG_FILE}"
  tail -n 8 "${LOG_FILE}" || true
}

stop_daemon() {
  cleanup_stale_pid
  if ! running_info="$(find_running_pid)"; then
    if has_fresh_soak_activity; then
      echo "tst2 soak has fresh samples but pid file is unavailable; cannot safely stop unknown process"
      return 1
    fi
    echo "tst2 soak not running"
    rm -f "${PID_FILE}" "${COMPAT_PID_FILE}" >/dev/null 2>&1 || true
    return 0
  fi

  local pids=()
  local pidf
  local pid
  local seen=" "
  for pidf in "${PID_FILE}" "${COMPAT_PID_FILE}"; do
    if [[ ! -f "${pidf}" ]]; then
      continue
    fi
    pid="$(cat "${pidf}")"
    if ! is_pid_running "${pid}"; then
      continue
    fi
    if [[ "${seen}" == *" ${pid} "* ]]; then
      continue
    fi
    seen="${seen}${pid} "
    pids+=("${pid}")
  done

  if [[ "${#pids[@]}" -eq 0 ]]; then
    rm -f "${PID_FILE}" "${COMPAT_PID_FILE}" >/dev/null 2>&1 || true
    echo "tst2 soak already stopped (stale pid removed)"
    return 0
  fi

  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[dry-run] kill ${pids[*]}"
    return 0
  fi

  for pid in "${pids[@]}"; do
    kill "${pid}" >/dev/null 2>&1 || true
  done
  for _ in $(seq 1 25); do
    all_stopped=true
    for pid in "${pids[@]}"; do
      if is_pid_running "${pid}"; then
        all_stopped=false
      fi
    done
    if [[ "${all_stopped}" == "true" ]]; then
      rm -f "${PID_FILE}" "${COMPAT_PID_FILE}" >/dev/null 2>&1 || true
      echo "tst2 soak stopped"
      return 0
    fi
    sleep 0.2
  done

  for pid in "${pids[@]}"; do
    kill -9 "${pid}" >/dev/null 2>&1 || true
  done
  rm -f "${PID_FILE}" "${COMPAT_PID_FILE}" >/dev/null 2>&1 || true
  echo "tst2 soak force stopped"
}

status_daemon() {
  cleanup_stale_pid

  if running_info="$(find_running_pid)"; then
    running_pid="${running_info%%|*}"
    running_pid_file="${running_info#*|}"
    if [[ "${running_pid_file}" != "${PID_FILE}" ]]; then
      echo "${running_pid}" >"${PID_FILE}"
    fi
    echo "tst2 soak daemon: running (pid=${running_pid}, pid_file=${running_pid_file})"
  elif has_fresh_soak_activity; then
    echo "tst2 soak daemon: running (pid=unknown, source=fresh-samples)"
  else
    echo "tst2 soak daemon: stopped"
  fi

  if [[ -f "${START_FILE}" ]]; then
    echo "tst2 soak start: $(cat "${START_FILE}")"
  fi
  if [[ -f "${LOG_FILE}" ]]; then
    echo "tst2 soak log tail:"
    tail -n 8 "${LOG_FILE}" || true
  fi

  if [[ "${STRICT_MODE}" == "true" ]]; then
    bash "${ROOT_DIR}/scripts/tst2_soak_status.sh" --strict
    return $?
  fi

  set +e
  bash "${ROOT_DIR}/scripts/tst2_soak_status.sh"
  local status_rc=$?
  set -e
  if [[ "${status_rc}" -ne 0 ]]; then
    echo "tst2 soak status guard not green (rc=${status_rc})"
  fi
}

COMMAND="${1:-status}"
if [[ $# -gt 0 ]]; then
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT_MODE=true
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    --control-url)
      shift
      CONTROL_URL="${1:-}"
      ;;
    --action-url)
      shift
      ACTION_URL="${1:-}"
      ;;
    --token)
      shift
      AUTH_TOKEN="${1:-}"
      ;;
    --duration)
      shift
      SOAK_DURATION_SECONDS="${1:-}"
      ;;
    --interval)
      shift
      SOAK_INTERVAL_SECONDS="${1:-}"
      ;;
    --probe-runs)
      shift
      SOAK_PROBE_RUN_COUNT="${1:-}"
      ;;
    --probe-workers)
      shift
      SOAK_PROBE_WORKERS="${1:-}"
      ;;
    --probe-each-round)
      shift
      SOAK_RUN_PROBE_EACH_ROUND="${1:-}"
      ;;
    --skip-service-start)
      shift
      SOAK_SKIP_SERVICE_START="${1:-}"
      ;;
    --fail-on-failed-delta)
      shift
      SOAK_FAIL_ON_FAILED_DELTA="${1:-}"
      ;;
    --max-failed-run-delta)
      shift
      SOAK_MAX_FAILED_RUN_DELTA="${1:-}"
      ;;
    --report-dir)
      shift
      SOAK_REPORT_DIR="${1:-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

case "${COMMAND}" in
  start)
    start_daemon
    ;;
  status)
    status_daemon
    ;;
  stop)
    stop_daemon
    ;;
  restart)
    stop_daemon
    start_daemon
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "unknown command: ${COMMAND}"
    usage
    exit 1
    ;;
esac
