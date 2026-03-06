#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${TST2_AUTOPILOT_PROFILE:-full}"
WATCH_INTERVAL_SECONDS="${TST2_AUTOPILOT_WATCH_INTERVAL_SECONDS:-300}"
WATCH_MAX_ROUNDS="${TST2_AUTOPILOT_WATCH_MAX_ROUNDS:-0}"
CHECKPOINT_EACH_ROUND="${TST2_AUTOPILOT_CHECKPOINT_EACH_ROUND:-true}"
SKIP_REHEARSAL=false
STRICT_MODE=false
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_autopilot.sh [options]

Options:
  --profile <full|local>         readiness profile to watch (default: full)
  --watch-interval <seconds>     watchdog polling interval (default: 300)
  --watch-max-rounds <n>         watchdog max rounds (0 means until ready)
  --checkpoint-each-round <bool> watchdog checkpoint per round (default: true)
  --skip-rehearsal               stop after readiness watch, skip T2 rehearsal
  --strict                       fail when readiness not reached before max rounds
  --dry-run                      print commands only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --profile"
        exit 1
      fi
      PROFILE="$1"
      ;;
    --watch-interval)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --watch-interval"
        exit 1
      fi
      WATCH_INTERVAL_SECONDS="$1"
      ;;
    --watch-max-rounds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --watch-max-rounds"
        exit 1
      fi
      WATCH_MAX_ROUNDS="$1"
      ;;
    --checkpoint-each-round)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --checkpoint-each-round"
        exit 1
      fi
      CHECKPOINT_EACH_ROUND="$1"
      ;;
    --skip-rehearsal)
      SKIP_REHEARSAL=true
      ;;
    --strict)
      STRICT_MODE=true
      ;;
    --dry-run)
      DRY_RUN=true
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

if [[ "${PROFILE}" != "full" && "${PROFILE}" != "local" ]]; then
  echo "unsupported --profile: ${PROFILE}"
  exit 1
fi
if ! [[ "${WATCH_INTERVAL_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${WATCH_INTERVAL_SECONDS}" -lt 1 ]]; then
  echo "--watch-interval must be an integer >= 1"
  exit 1
fi
if ! [[ "${WATCH_MAX_ROUNDS}" =~ ^[0-9]+$ ]]; then
  echo "--watch-max-rounds must be an integer >= 0"
  exit 1
fi
if [[ "${CHECKPOINT_EACH_ROUND}" != "true" && "${CHECKPOINT_EACH_ROUND}" != "false" ]]; then
  echo "--checkpoint-each-round must be true|false"
  exit 1
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run][1/3] bash scripts/stationctl.sh soak start"
  echo "[dry-run][2/3] bash scripts/stationctl.sh tst2-watch --profile ${PROFILE} --interval ${WATCH_INTERVAL_SECONDS} --max-rounds ${WATCH_MAX_ROUNDS} --checkpoint-each-round ${CHECKPOINT_EACH_ROUND}${STRICT_MODE:+ --strict}"
  if [[ "${SKIP_REHEARSAL}" == "true" ]]; then
    echo "[dry-run][3/3] skip rehearsal"
  else
    echo "[dry-run][3/3] bash scripts/stationctl.sh tst2-rehearsal --strict"
  fi
  exit 0
fi

echo "[1/3] ensure soak writer active"
bash "${ROOT_DIR}/scripts/stationctl.sh" soak start

echo "[2/3] watch readiness"
watch_cmd=(
  bash
  "${ROOT_DIR}/scripts/stationctl.sh"
  tst2-watch
  --profile
  "${PROFILE}"
  --interval
  "${WATCH_INTERVAL_SECONDS}"
  --max-rounds
  "${WATCH_MAX_ROUNDS}"
  --checkpoint-each-round
  "${CHECKPOINT_EACH_ROUND}"
)
if [[ "${STRICT_MODE}" == "true" ]]; then
  watch_cmd+=(--strict)
fi

set +e
watch_output="$("${watch_cmd[@]}" 2>&1)"
watch_rc=$?
set -e
printf '%s\n' "${watch_output}"

watch_report="$(printf '%s\n' "${watch_output}" | awk -F= '/^watchdog_report=/{print $2}' | tail -n 1)"
watch_passed="$(printf '%s\n' "${watch_output}" | awk -F= '/^watchdog_passed=/{print $2}' | tail -n 1)"
if [[ -z "${watch_passed}" ]]; then
  watch_passed=false
fi

if [[ "${watch_rc}" -ne 0 && "${STRICT_MODE}" == "true" ]]; then
  echo "autopilot_ready=false"
  echo "autopilot_report=${watch_report}"
  exit "${watch_rc}"
fi

if [[ "${watch_passed}" != "true" ]]; then
  echo "autopilot_ready=false"
  echo "autopilot_report=${watch_report}"
  if [[ "${STRICT_MODE}" == "true" ]]; then
    exit 1
  fi
  exit 0
fi

if [[ "${SKIP_REHEARSAL}" == "true" ]]; then
  echo "autopilot_ready=true"
  echo "autopilot_report=${watch_report}"
  echo "autopilot_rehearsal=skipped"
  exit 0
fi

echo "[3/3] trigger strict T2 rehearsal"
bash "${ROOT_DIR}/scripts/stationctl.sh" tst2-rehearsal --strict
bash "${ROOT_DIR}/scripts/stationctl.sh" tst2-rehearsal-latest --strict

echo "autopilot_ready=true"
echo "autopilot_report=${watch_report}"
echo "autopilot_rehearsal=passed"
