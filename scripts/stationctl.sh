#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMAND_CENTER_DIR="${ROOT_DIR}/command_center"
CONTROL_CENTER_DIR="${ROOT_DIR}/control_center"
ACTION_LAYER_DIR="${ROOT_DIR}/action_layer"
CONTROL_VENV_PYTHON="${CONTROL_CENTER_DIR}/.venv/bin/python"
RUN_DIR="${ROOT_DIR}/.wherecode/run"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  bash scripts/stationctl.sh [--dry-run] <command> [target]

Commands:
  install [all|command-center|control-center|action-layer]
  dev [all|command-center|control-center|action-layer]
  start [all|command-center|control-center|action-layer]
  stop [all|command-center|control-center|action-layer]
  status [all|command-center|control-center|action-layer]
  check
  help

Examples:
  bash scripts/stationctl.sh install all
  bash scripts/stationctl.sh dev all
  bash scripts/stationctl.sh start all
  bash scripts/stationctl.sh status all
  bash scripts/stationctl.sh stop all
  bash scripts/stationctl.sh check
EOF
}

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] $*"
    return 0
  fi
  "$@"
}

ensure_pnpm() {
  if ! command -v pnpm >/dev/null 2>&1; then
    echo "pnpm not found. Install pnpm first."
    exit 1
  fi
}

ensure_python3() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3 first."
    exit 1
  fi
}

pid_file() {
  local target="$1"
  echo "${RUN_DIR}/${target}.pid"
}

log_file() {
  local target="$1"
  echo "${RUN_DIR}/${target}.log"
}

is_pid_running() {
  local pid="$1"
  if [[ -z "${pid}" ]]; then
    return 1
  fi
  kill -0 "${pid}" >/dev/null 2>&1
}

cleanup_stale_pid() {
  local target="$1"
  local pidf
  pidf="$(pid_file "${target}")"
  if [[ ! -f "${pidf}" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "${pidf}")"
  if is_pid_running "${pid}"; then
    return 0
  fi
  rm -f "${pidf}"
}

install_command_center() {
  ensure_pnpm
  run pnpm --dir "${COMMAND_CENTER_DIR}" install
}

install_control_center() {
  ensure_python3
  if [[ ! -x "${CONTROL_VENV_PYTHON}" ]]; then
    run python3 -m venv "${CONTROL_CENTER_DIR}/.venv"
  fi
  run "${CONTROL_VENV_PYTHON}" -m pip install -r "${CONTROL_CENTER_DIR}/requirements.txt"
}

install_action_layer() {
  if [[ -f "${ACTION_LAYER_DIR}/requirements.txt" ]]; then
    ensure_python3
    if [[ ! -x "${ACTION_LAYER_DIR}/.venv/bin/python" ]]; then
      run python3 -m venv "${ACTION_LAYER_DIR}/.venv"
    fi
    run "${ACTION_LAYER_DIR}/.venv/bin/python" -m pip install -r "${ACTION_LAYER_DIR}/requirements.txt"
    return 0
  fi
  if [[ -f "${ACTION_LAYER_DIR}/package.json" ]]; then
    ensure_pnpm
    run pnpm --dir "${ACTION_LAYER_DIR}" install
    return 0
  fi
  echo "action-layer has no dependency manifest; using stdlib runtime, nothing to install."
}

dev_command_center() {
  ensure_pnpm
  run pnpm --dir "${COMMAND_CENTER_DIR}" dev
}

dev_control_center() {
  run bash "${CONTROL_CENTER_DIR}/run.sh"
}

dev_action_layer() {
  if [[ -x "${ACTION_LAYER_DIR}/run.sh" ]]; then
    run bash "${ACTION_LAYER_DIR}/run.sh"
    return 0
  fi
  echo "action-layer has no runtime entrypoint yet; skip start."
}

start_service() {
  local target="$1"
  cleanup_stale_pid "${target}"

  local pidf logf
  pidf="$(pid_file "${target}")"
  logf="$(log_file "${target}")"

  if [[ -f "${pidf}" ]]; then
    local existing_pid
    existing_pid="$(cat "${pidf}")"
    if is_pid_running "${existing_pid}"; then
      echo "${target} already running (pid=${existing_pid})"
      return 0
    fi
    rm -f "${pidf}"
  fi

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    case "${target}" in
      command-center)
        echo "[dry-run] nohup pnpm --dir ${COMMAND_CENTER_DIR} dev > ${logf} 2>&1 &"
        ;;
      control-center)
        echo "[dry-run] nohup bash ${CONTROL_CENTER_DIR}/run.sh > ${logf} 2>&1 &"
        ;;
      action-layer)
        echo "[dry-run] nohup bash ${ACTION_LAYER_DIR}/run.sh > ${logf} 2>&1 &"
        ;;
    esac
    return 0
  fi

  mkdir -p "${RUN_DIR}"
  case "${target}" in
    command-center)
      ensure_pnpm
      nohup pnpm --dir "${COMMAND_CENTER_DIR}" dev >"${logf}" 2>&1 &
      ;;
    control-center)
      nohup bash "${CONTROL_CENTER_DIR}/run.sh" >"${logf}" 2>&1 &
      ;;
    action-layer)
      if [[ ! -x "${ACTION_LAYER_DIR}/run.sh" ]]; then
        echo "action-layer has no runtime entrypoint yet; skip start."
        return 0
      fi
      nohup bash "${ACTION_LAYER_DIR}/run.sh" >"${logf}" 2>&1 &
      ;;
    *)
      echo "unknown start target: ${target}"
      exit 1
      ;;
  esac

  local pid="$!"
  echo "${pid}" >"${pidf}"
  echo "${target} started (pid=${pid})"
  echo "log: ${logf}"
}

stop_service() {
  local target="$1"
  local pidf
  pidf="$(pid_file "${target}")"

  if [[ ! -f "${pidf}" ]]; then
    echo "${target} not running (no pid file)"
    return 0
  fi

  local pid
  pid="$(cat "${pidf}")"
  if ! is_pid_running "${pid}"; then
    rm -f "${pidf}"
    echo "${target} already stopped (stale pid removed)"
    return 0
  fi

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] kill ${pid}  # ${target}"
    return 0
  fi

  kill "${pid}" >/dev/null 2>&1 || true
  for _ in $(seq 1 25); do
    if ! is_pid_running "${pid}"; then
      rm -f "${pidf}"
      echo "${target} stopped"
      return 0
    fi
    sleep 0.2
  done

  kill -9 "${pid}" >/dev/null 2>&1 || true
  rm -f "${pidf}"
  echo "${target} force stopped"
}

status_service() {
  local target="$1"
  local pidf
  pidf="$(pid_file "${target}")"
  if [[ ! -f "${pidf}" ]]; then
    echo "${target}: stopped"
    return 0
  fi

  local pid
  pid="$(cat "${pidf}")"
  if is_pid_running "${pid}"; then
    echo "${target}: running (pid=${pid})"
    return 0
  fi

  echo "${target}: stopped (stale pid file)"
}

do_for_target() {
  local op="$1"
  local target="$2"
  case "${target}" in
    all)
      "${op}" command-center
      "${op}" control-center
      "${op}" action-layer
      ;;
    command-center|control-center|action-layer)
      "${op}" "${target}"
      ;;
    *)
      echo "unknown target: ${target}"
      usage
      exit 1
      ;;
  esac
}

dev_all() {
  ensure_pnpm
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] bash ${CONTROL_CENTER_DIR}/run.sh"
    echo "[dry-run] pnpm --dir ${COMMAND_CENTER_DIR} dev"
    if [[ -x "${ACTION_LAYER_DIR}/run.sh" ]]; then
      echo "[dry-run] bash ${ACTION_LAYER_DIR}/run.sh"
    else
      echo "[dry-run] action-layer has no runtime entrypoint yet; skip start."
    fi
    return 0
  fi

  local pids=()
  trap 'for pid in "${pids[@]}"; do kill "${pid}" 2>/dev/null || true; done' INT TERM EXIT

  bash "${CONTROL_CENTER_DIR}/run.sh" &
  pids+=("$!")
  pnpm --dir "${COMMAND_CENTER_DIR}" dev &
  pids+=("$!")

  if [[ -x "${ACTION_LAYER_DIR}/run.sh" ]]; then
    bash "${ACTION_LAYER_DIR}/run.sh" &
    pids+=("$!")
  else
    echo "action-layer has no runtime entrypoint yet; skip start."
  fi

  wait -n "${pids[@]}"
  local exit_code=$?
  for pid in "${pids[@]}"; do
    kill "${pid}" 2>/dev/null || true
  done
  wait || true
  exit "${exit_code}"
}

main() {
  if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    shift
  fi

  local command="${1:-help}"
  local target="${2:-all}"

  case "${command}" in
    help|-h|--help)
      usage
      ;;
    install)
      case "${target}" in
        all)
          install_command_center
          install_control_center
          install_action_layer
          ;;
        command-center)
          install_command_center
          ;;
        control-center)
          install_control_center
          ;;
        action-layer)
          install_action_layer
          ;;
        *)
          echo "unknown install target: ${target}"
          usage
          exit 1
          ;;
      esac
      ;;
    dev)
      case "${target}" in
        all)
          dev_all
          ;;
        command-center)
          dev_command_center
          ;;
        control-center)
          dev_control_center
          ;;
        action-layer)
          dev_action_layer
          ;;
        *)
          echo "unknown dev target: ${target}"
          usage
          exit 1
          ;;
      esac
      ;;
    start)
      do_for_target start_service "${target}"
      ;;
    stop)
      do_for_target stop_service "${target}"
      ;;
    status)
      do_for_target status_service "${target}"
      ;;
    check)
      run bash "${ROOT_DIR}/scripts/check_all.sh"
      ;;
    *)
      echo "unknown command: ${command}"
      usage
      exit 1
      ;;
  esac
}

main "$@"
