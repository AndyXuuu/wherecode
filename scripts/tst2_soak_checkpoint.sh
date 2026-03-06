#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.wherecode/run"
REPORT_DIR="${SOAK_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
STRICT_MODE=false
REQUIRE_DAEMON_RUNNING="${SOAK_CHECKPOINT_STRICT_REQUIRE_DAEMON:-false}"
OUTPUT_PATH=""

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_soak_checkpoint.sh [--strict] [--require-daemon-running] [--output <path>]

Options:
  --strict                   exit non-zero when guard_passed=false
  --require-daemon-running   with --strict, also require soak daemon running
  --output <path>            write checkpoint report to a specific markdown file

Env:
  SOAK_CHECKPOINT_STRICT_REQUIRE_DAEMON=true|false (default: false)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT_MODE=true
      ;;
    --require-daemon-running)
      REQUIRE_DAEMON_RUNNING=true
      ;;
    --output)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --output"
        exit 1
      fi
      OUTPUT_PATH="$1"
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

mkdir -p "${REPORT_DIR}"

if [[ -z "${OUTPUT_PATH}" ]]; then
  stamp="$(date -u +"%Y%m%dT%H%M%SZ")"
  OUTPUT_PATH="${REPORT_DIR}/${stamp}-tst2-live-checkpoint-auto.md"
fi

status_raw="$(bash "${ROOT_DIR}/scripts/tst2_soak_status.sh" 2>&1 || true)"
progress_raw="$(bash "${ROOT_DIR}/scripts/tst2_progress_report.sh" --profile full 2>&1 || true)"

daemon_running=false
daemon_pid=""
pid_file="${RUN_DIR}/tst2-soak.pid"
if [[ -f "${pid_file}" ]]; then
  daemon_pid="$(cat "${pid_file}")"
  if [[ -n "${daemon_pid}" ]] && kill -0 "${daemon_pid}" >/dev/null 2>&1; then
    daemon_running=true
  fi
fi

daemon_start_meta=""
if [[ -f "${RUN_DIR}/tst2-soak.start" ]]; then
  daemon_start_meta="$(cat "${RUN_DIR}/tst2-soak.start")"
fi

log_tail=""
if [[ -f "${RUN_DIR}/tst2-soak.log" ]]; then
  log_tail="$(tail -n 8 "${RUN_DIR}/tst2-soak.log" 2>/dev/null || true)"
fi

python3 - "${OUTPUT_PATH}" "${status_raw}" "${daemon_running}" "${daemon_pid}" "${daemon_start_meta}" "${log_tail}" "${progress_raw}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

output_path = Path(sys.argv[1])
status_raw = sys.argv[2]
daemon_running = sys.argv[3] == "true"
daemon_pid = sys.argv[4]
daemon_start_meta = sys.argv[5]
log_tail = sys.argv[6]
progress_raw = sys.argv[7]

now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
status_payload: dict[str, object] | None = None
status_parse_error = ""
progress_payload: dict[str, object] | None = None
progress_parse_error = ""
try:
    parsed = json.loads(status_raw)
    if isinstance(parsed, dict):
        status_payload = parsed
except Exception as exc:  # noqa: BLE001
    status_parse_error = str(exc)

try:
    parsed_progress = json.loads(progress_raw)
    if isinstance(parsed_progress, dict):
        progress_payload = parsed_progress
except Exception as exc:  # noqa: BLE001
    progress_parse_error = str(exc)

lines: list[str] = []
lines.append(f"# TST2 live checkpoint ({now_iso[:10]})")
lines.append("")
lines.append("## Runtime")
lines.append("")
lines.append(f"- captured_at_utc: `{now_iso}`")
lines.append(f"- daemon_running: `{str(daemon_running).lower()}`")
if daemon_pid:
    lines.append(f"- daemon_pid: `{daemon_pid}`")
if daemon_start_meta:
    lines.append(f"- daemon_start_meta: `{daemon_start_meta}`")
lines.append("")

lines.append("## Guard snapshot")
lines.append("")
if status_payload is None:
    lines.append("- status_parse_ok: `false`")
    lines.append(f"- status_parse_error: `{status_parse_error or 'invalid_json'}`")
    lines.append(f"- status_raw: `{status_raw}`")
else:
    lines.append("- status_parse_ok: `true`")
    for key in (
        "samples_file",
        "samples_total",
        "latest_round",
        "failed_run_count_delta",
        "probe_failed_rounds",
        "last_sample_age_seconds",
        "expected_interval_seconds",
        "max_staleness_seconds",
        "stale",
        "guard_drift_passed",
        "guard_passed",
        "summary",
    ):
        if key in status_payload:
            value = status_payload[key]
            lines.append(f"- {key}: `{value}`")
lines.append("")

lines.append("## Full gate forecast")
lines.append("")
if progress_payload is None:
    lines.append("- progress_parse_ok: `false`")
    lines.append(f"- progress_parse_error: `{progress_parse_error or 'invalid_json'}`")
    lines.append(f"- progress_raw: `{progress_raw}`")
else:
    lines.append("- progress_parse_ok: `true`")
    for key in (
        "samples_total",
        "samples_remaining",
        "coverage_progress_pct",
        "coverage_remaining_seconds",
        "forecast_rounds_remaining",
        "forecast_hours_remaining",
        "projected_ready_at_utc",
        "summary",
    ):
        if key in progress_payload:
            value = progress_payload[key]
            lines.append(f"- {key}: `{value}`")
lines.append("")

lines.append("## Soak log tail")
lines.append("")
if log_tail.strip():
    lines.append("```text")
    lines.extend(log_tail.splitlines())
    lines.append("```")
else:
    lines.append("- log tail is empty")

output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(output_path)
PY

guard_ok=false
if python3 - "${status_raw}" <<'PY'
from __future__ import annotations

import json
import sys

raw = sys.argv[1]
try:
    payload = json.loads(raw)
except Exception:  # noqa: BLE001
    print("false")
    raise SystemExit(0)
print("true" if bool(payload.get("guard_passed")) else "false")
PY
then
  guard_ok="$(python3 - "${status_raw}" <<'PY'
from __future__ import annotations

import json
import sys

raw = sys.argv[1]
try:
    payload = json.loads(raw)
except Exception:  # noqa: BLE001
    print("false")
    raise SystemExit(0)
print("true" if bool(payload.get("guard_passed")) else "false")
PY
)"
else
  guard_ok=false
fi

echo "checkpoint_written=${OUTPUT_PATH}"
echo "guard_passed=${guard_ok}"
echo "daemon_running=${daemon_running}"
echo "strict_mode=${STRICT_MODE}"
echo "strict_require_daemon_running=${REQUIRE_DAEMON_RUNNING}"

progress_metrics="$(python3 - "${progress_raw}" <<'PY'
from __future__ import annotations

import json
import sys

raw = sys.argv[1]
fields = ["", "", "", ""]
try:
    payload = json.loads(raw)
except Exception:  # noqa: BLE001
    print("\n".join(fields))
    raise SystemExit(0)

if not isinstance(payload, dict):
    print("\n".join(fields))
    raise SystemExit(0)

fields = [
    payload.get("samples_remaining", ""),
    payload.get("coverage_remaining_seconds", ""),
    payload.get("forecast_hours_remaining", ""),
    payload.get("projected_ready_at_utc", ""),
]
print("\n".join("" if value is None else str(value) for value in fields))
PY
)"
progress_samples_remaining=""
progress_coverage_remaining_seconds=""
progress_forecast_hours_remaining=""
progress_projected_ready_at_utc=""
{
  IFS= read -r progress_samples_remaining || true
  IFS= read -r progress_coverage_remaining_seconds || true
  IFS= read -r progress_forecast_hours_remaining || true
  IFS= read -r progress_projected_ready_at_utc || true
} <<<"${progress_metrics}"
echo "full_profile_samples_remaining=${progress_samples_remaining}"
echo "full_profile_coverage_remaining_seconds=${progress_coverage_remaining_seconds}"
echo "full_profile_forecast_hours_remaining=${progress_forecast_hours_remaining}"
echo "full_profile_projected_ready_at_utc=${progress_projected_ready_at_utc}"

if [[ "${STRICT_MODE}" == "true" ]]; then
  if [[ "${guard_ok}" != "true" ]]; then
    exit 1
  fi
  if [[ "${REQUIRE_DAEMON_RUNNING}" == "true" && "${daemon_running}" != "true" ]]; then
    exit 1
  fi
fi
