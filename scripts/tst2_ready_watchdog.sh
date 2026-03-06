#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${TST2_READY_WATCH_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
PROFILE="${TST2_READY_WATCH_PROFILE:-full}"
WATCH_INTERVAL_SECONDS="${TST2_READY_WATCH_INTERVAL_SECONDS:-300}"
WATCH_MAX_ROUNDS="${TST2_READY_WATCH_MAX_ROUNDS:-0}"
CHECKPOINT_EACH_ROUND="${TST2_READY_WATCH_CHECKPOINT_EACH_ROUND:-true}"
STRICT_MODE=false
OUTPUT_PATH=""

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_ready_watchdog.sh [options]

Options:
  --profile <full|local>        gate profile to watch (default: full)
  --interval <seconds>          polling interval (default: 300)
  --max-rounds <n>              stop after n rounds (0 means no limit, default: 0)
  --checkpoint-each-round <bool> run soak-checkpoint each round (default: true)
  --output <path>               write markdown report to custom path
  --strict                      exit non-zero when not ready before max-rounds
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
    --interval)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --interval"
        exit 1
      fi
      WATCH_INTERVAL_SECONDS="$1"
      ;;
    --max-rounds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --max-rounds"
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
    --output)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --output"
        exit 1
      fi
      OUTPUT_PATH="$1"
      ;;
    --strict)
      STRICT_MODE=true
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
  echo "unsupported profile: ${PROFILE}"
  exit 1
fi
if ! [[ "${WATCH_INTERVAL_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${WATCH_INTERVAL_SECONDS}" -lt 1 ]]; then
  echo "--interval must be an integer >= 1"
  exit 1
fi
if ! [[ "${WATCH_MAX_ROUNDS}" =~ ^[0-9]+$ ]]; then
  echo "--max-rounds must be an integer >= 0"
  exit 1
fi
if [[ "${CHECKPOINT_EACH_ROUND}" != "true" && "${CHECKPOINT_EACH_ROUND}" != "false" ]]; then
  echo "--checkpoint-each-round must be true|false"
  exit 1
fi

mkdir -p "${REPORT_DIR}"
if [[ -z "${OUTPUT_PATH}" ]]; then
  stamp="$(date -u +"%Y%m%dT%H%M%SZ")"
  OUTPUT_PATH="${REPORT_DIR}/${stamp}-tst2-ready-watchdog.md"
fi
mkdir -p "$(dirname "${OUTPUT_PATH}")"

{
  echo "# TST2 ready watchdog"
  echo
  echo "- started_at_utc: \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
  echo "- profile: \`${PROFILE}\`"
  echo "- interval_seconds: \`${WATCH_INTERVAL_SECONDS}\`"
  echo "- max_rounds: \`${WATCH_MAX_ROUNDS}\`"
  echo "- checkpoint_each_round: \`${CHECKPOINT_EACH_ROUND}\`"
  echo "- strict_mode: \`${STRICT_MODE}\`"
  echo
} >"${OUTPUT_PATH}"

round=0
final_passed=false
last_progress_json=""
last_gate_json=""

while true; do
  round=$((round + 1))
  captured_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  set +e
  progress_out="$(bash "${ROOT_DIR}/scripts/tst2_progress_report.sh" --profile "${PROFILE}" 2>&1)"
  progress_rc=$?
  set -e

  parsed_progress="$(
    python3 - "${progress_out}" <<'PY'
from __future__ import annotations

import json
import sys

raw = sys.argv[1]
try:
    payload = json.loads(raw)
except Exception:  # noqa: BLE001
    print("parse_ok=false")
    print("passed=false")
    print("samples_total=")
    print("samples_remaining=")
    print("coverage_remaining_seconds=")
    print("forecast_hours_remaining=")
    print("projected_ready_at_utc=")
    print(f"summary={raw}")
    raise SystemExit(0)

if not isinstance(payload, dict):
    print("parse_ok=false")
    print("passed=false")
    print("samples_total=")
    print("samples_remaining=")
    print("coverage_remaining_seconds=")
    print("forecast_hours_remaining=")
    print("projected_ready_at_utc=")
    print(f"summary={raw}")
    raise SystemExit(0)

print("parse_ok=true")
print(f"passed={'true' if bool(payload.get('passed')) else 'false'}")
print(f"samples_total={payload.get('samples_total', '')}")
print(f"samples_remaining={payload.get('samples_remaining', '')}")
print(f"coverage_remaining_seconds={payload.get('coverage_remaining_seconds', '')}")
print(f"forecast_hours_remaining={payload.get('forecast_hours_remaining', '')}")
print(f"projected_ready_at_utc={payload.get('projected_ready_at_utc', '') or ''}")
print(f"summary={payload.get('summary', '')}")
PY
  )"

  progress_parse_ok=""
  progress_passed=""
  progress_samples_total=""
  progress_samples_remaining=""
  progress_coverage_remaining=""
  progress_forecast_hours=""
  progress_projected_ready_at=""
  progress_summary=""
  while IFS='=' read -r key value; do
    case "${key}" in
      parse_ok) progress_parse_ok="${value}" ;;
      passed) progress_passed="${value}" ;;
      samples_total) progress_samples_total="${value}" ;;
      samples_remaining) progress_samples_remaining="${value}" ;;
      coverage_remaining_seconds) progress_coverage_remaining="${value}" ;;
      forecast_hours_remaining) progress_forecast_hours="${value}" ;;
      projected_ready_at_utc) progress_projected_ready_at="${value}" ;;
      summary) progress_summary="${value}" ;;
    esac
  done <<<"${parsed_progress}"

  checkpoint_rc=""
  checkpoint_path=""
  checkpoint_guard=""
  if [[ "${CHECKPOINT_EACH_ROUND}" == "true" ]]; then
    set +e
    checkpoint_out="$(bash "${ROOT_DIR}/scripts/tst2_soak_checkpoint.sh" --strict 2>&1)"
    checkpoint_rc=$?
    set -e
    checkpoint_path="$(printf '%s\n' "${checkpoint_out}" | awk -F= '/^checkpoint_written=/{print $2}' | tail -n 1)"
    checkpoint_guard="$(printf '%s\n' "${checkpoint_out}" | awk -F= '/^guard_passed=/{print $2}' | tail -n 1)"
  fi

  echo "tst2_watch_round=${round} profile=${PROFILE} passed=${progress_passed} samples_total=${progress_samples_total} samples_remaining=${progress_samples_remaining} coverage_remaining_seconds=${progress_coverage_remaining} forecast_hours_remaining=${progress_forecast_hours}"

  {
    echo "## Round ${round}"
    echo
    echo "- captured_at_utc: \`${captured_at}\`"
    echo "- progress_rc: \`${progress_rc}\`"
    echo "- progress_parse_ok: \`${progress_parse_ok}\`"
    echo "- progress_passed: \`${progress_passed}\`"
    echo "- samples_total: \`${progress_samples_total}\`"
    echo "- samples_remaining: \`${progress_samples_remaining}\`"
    echo "- coverage_remaining_seconds: \`${progress_coverage_remaining}\`"
    echo "- forecast_hours_remaining: \`${progress_forecast_hours}\`"
    echo "- projected_ready_at_utc: \`${progress_projected_ready_at}\`"
    echo "- summary: \`${progress_summary}\`"
    if [[ "${CHECKPOINT_EACH_ROUND}" == "true" ]]; then
      echo "- checkpoint_rc: \`${checkpoint_rc}\`"
      echo "- checkpoint_guard_passed: \`${checkpoint_guard}\`"
      if [[ -n "${checkpoint_path}" ]]; then
        echo "- checkpoint_report: \`${checkpoint_path}\`"
      fi
    fi
    echo
  } >>"${OUTPUT_PATH}"

  last_progress_json="${progress_out}"

  if [[ "${progress_parse_ok}" == "true" && "${progress_passed}" == "true" ]]; then
    set +e
    gate_out="$(bash "${ROOT_DIR}/scripts/v3_milestone_gate.sh" --milestone tst2-ready --tst2-profile "${PROFILE}" --strict 2>&1)"
    gate_rc=$?
    set -e
    last_gate_json="${gate_out}"

    {
      echo "## Gate verification"
      echo
      echo "- gate_rc: \`${gate_rc}\`"
      echo "- gate_output: \`${gate_out}\`"
      echo
    } >>"${OUTPUT_PATH}"

    if [[ "${gate_rc}" -eq 0 ]]; then
      final_passed=true
      break
    fi
  fi

  if [[ "${WATCH_MAX_ROUNDS}" -gt 0 && "${round}" -ge "${WATCH_MAX_ROUNDS}" ]]; then
    break
  fi

  sleep "${WATCH_INTERVAL_SECONDS}"
done

{
  echo "## Final"
  echo
  echo "- finished_at_utc: \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
  echo "- rounds_executed: \`${round}\`"
  echo "- final_passed: \`${final_passed}\`"
  echo
} >>"${OUTPUT_PATH}"

echo "watchdog_report=${OUTPUT_PATH}"
echo "watchdog_rounds=${round}"
echo "watchdog_passed=${final_passed}"

if [[ "${STRICT_MODE}" == "true" && "${final_passed}" != "true" ]]; then
  exit 1
fi
