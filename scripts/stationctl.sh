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
  soak [start|status|stop|restart] [soak-options]
  soak-checkpoint [--strict] [--require-daemon-running] [--output <path>]
  tst2-rehearsal [control_url] [action_url] [--strict]
  tst2-rehearsal-latest [--path-only] [--strict]
  tst2-progress [--profile full|local] [--strict]
  tst2-watch [--profile full|local] [--interval <seconds>] [--max-rounds <n>] [--strict]
  tst2-autopilot [--profile full|local] [--watch-interval <seconds>] [--watch-max-rounds <n>] [--strict]
  mb3-dry-run [control_url] [mb3-options]
  action-llm-check [action_layer_url] [role] [module_key] [text]
  readme-phase-sync [--dry-run] [--strict]
  check [quick|dev|release|ops]
  help

Examples:
  bash scripts/stationctl.sh install all
  bash scripts/stationctl.sh dev all
  bash scripts/stationctl.sh start all
  bash scripts/stationctl.sh status all
  bash scripts/stationctl.sh stop all
  bash scripts/stationctl.sh soak start
  bash scripts/stationctl.sh soak status --strict
  bash scripts/stationctl.sh soak-checkpoint --strict
  bash scripts/stationctl.sh tst2-rehearsal
  bash scripts/stationctl.sh tst2-rehearsal-latest
  bash scripts/stationctl.sh tst2-progress --profile full
  bash scripts/stationctl.sh tst2-watch --profile full --interval 60 --max-rounds 10
  bash scripts/stationctl.sh tst2-autopilot --profile full --watch-interval 60 --watch-max-rounds 120
  bash scripts/stationctl.sh mb3-dry-run
  bash scripts/stationctl.sh action-llm-check http://127.0.0.1:8100
  bash scripts/stationctl.sh readme-phase-sync --strict
  bash scripts/stationctl.sh check
  bash scripts/stationctl.sh check quick
  bash scripts/stationctl.sh check release
  bash scripts/stationctl.sh check ops
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
  sleep 0.5
  if ! is_pid_running "${pid}"; then
    rm -f "${pidf}"
    echo "${target} failed to start (process exited early)"
    if [[ -f "${logf}" ]]; then
      echo "last logs:"
      tail -n 20 "${logf}" || true
    fi
    return 1
  fi
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

run_soak() {
  local soak_action="${1:-status}"
  shift || true
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    bash "${ROOT_DIR}/scripts/tst2_soak_daemon.sh" "${soak_action}" --dry-run "$@"
    return 0
  fi
  bash "${ROOT_DIR}/scripts/tst2_soak_daemon.sh" "${soak_action}" "$@"
}

run_soak_checkpoint() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] bash scripts/tst2_soak_checkpoint.sh --output /tmp/tst2-soak-checkpoint-dry-run.md"
    bash "${ROOT_DIR}/scripts/tst2_soak_checkpoint.sh" --output "/tmp/tst2-soak-checkpoint-dry-run.md"
    return 0
  fi
  bash "${ROOT_DIR}/scripts/tst2_soak_checkpoint.sh" "$@"
}

run_tst2_rehearsal() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    bash "${ROOT_DIR}/scripts/tst2_t2_release_rehearsal.sh" --dry-run "$@"
    return 0
  fi
  bash "${ROOT_DIR}/scripts/tst2_t2_release_rehearsal.sh" "$@"
}

run_tst2_rehearsal_latest() {
  bash "${ROOT_DIR}/scripts/tst2_t2_rehearsal_latest.sh" "$@"
}

run_tst2_progress() {
  bash "${ROOT_DIR}/scripts/tst2_progress_report.sh" "$@"
}

run_tst2_watch() {
  bash "${ROOT_DIR}/scripts/tst2_ready_watchdog.sh" "$@"
}

run_tst2_autopilot() {
  bash "${ROOT_DIR}/scripts/tst2_autopilot.sh" "$@"
}

run_mb3_dry_run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    bash "${ROOT_DIR}/scripts/mb3_dry_run_seed.sh" --dry-run "$@"
    return 0
  fi
  bash "${ROOT_DIR}/scripts/mb3_dry_run_seed.sh" "$@"
}

run_action_llm_check() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] bash ${ROOT_DIR}/scripts/action_layer_llm_check.sh $*"
    return 0
  fi
  bash "${ROOT_DIR}/scripts/action_layer_llm_check.sh" "$@"
}

run_readme_phase_sync() {
  bash "${ROOT_DIR}/scripts/readme_phase_sync.sh" "$@"
}

run_check() {
  local scope="${1:-quick}"
  case "${scope}" in
    quick|dev|release|ops)
      ;;
    *)
      echo "unknown check scope: ${scope}"
      echo "allowed: quick|dev|release|ops"
      return 1
      ;;
  esac
  run bash "${ROOT_DIR}/scripts/check_all.sh" "${scope}"
}

main() {
  if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    shift
  fi

  local command="${1:-help}"
  if [[ $# -gt 0 ]]; then
    shift
  fi

  if [[ "${command}" == "soak" ]]; then
    local soak_action="${1:-status}"
    if [[ "${soak_action}" == --* ]]; then
      set -- "${soak_action}" "$@"
      soak_action="status"
    else
      if [[ $# -gt 0 ]]; then
        shift
      fi
    fi
    run_soak "${soak_action}" "$@"
    return
  fi

  if [[ "${command}" == "soak-checkpoint" ]]; then
    run_soak_checkpoint "$@"
    return
  fi

  if [[ "${command}" == "tst2-rehearsal" ]]; then
    run_tst2_rehearsal "$@"
    return
  fi

  if [[ "${command}" == "tst2-rehearsal-latest" ]]; then
    run_tst2_rehearsal_latest "$@"
    return
  fi

  if [[ "${command}" == "tst2-progress" ]]; then
    run_tst2_progress "$@"
    return
  fi

  if [[ "${command}" == "tst2-watch" ]]; then
    run_tst2_watch "$@"
    return
  fi

  if [[ "${command}" == "tst2-autopilot" ]]; then
    run_tst2_autopilot "$@"
    return
  fi

  if [[ "${command}" == "mb3-dry-run" ]]; then
    run_mb3_dry_run "$@"
    return
  fi

  if [[ "${command}" == "action-llm-check" ]]; then
    run_action_llm_check "$@"
    return
  fi

  if [[ "${command}" == "readme-phase-sync" ]]; then
    run_readme_phase_sync "$@"
    return
  fi

  if [[ "${command}" == "check" ]]; then
    run_check "$@"
    return
  fi

  local target="${1:-all}"

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
    *)
      echo "unknown command: ${command}"
      usage
      exit 1
      ;;
  esac
}

main "$@"
