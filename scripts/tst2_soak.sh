#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_URL="${1:-http://127.0.0.1:8000}"
ACTION_URL="${2:-http://127.0.0.1:8100}"
SOAK_DURATION_SECONDS="${SOAK_DURATION_SECONDS:-86400}"
SOAK_INTERVAL_SECONDS="${SOAK_INTERVAL_SECONDS:-300}"
SOAK_PROBE_RUN_COUNT="${SOAK_PROBE_RUN_COUNT:-2}"
SOAK_PROBE_WORKERS="${SOAK_PROBE_WORKERS:-1}"
SOAK_RUN_PROBE_EACH_ROUND="${SOAK_RUN_PROBE_EACH_ROUND:-true}"
SOAK_SKIP_SERVICE_START="${SOAK_SKIP_SERVICE_START:-false}"
SOAK_FAIL_ON_FAILED_DELTA="${SOAK_FAIL_ON_FAILED_DELTA:-true}"
SOAK_MAX_FAILED_RUN_DELTA="${SOAK_MAX_FAILED_RUN_DELTA:-0}"
REPORT_DIR="${SOAK_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
STARTED_CONTROL_CENTER=0
STARTED_ACTION_LAYER=0

if ! [[ "${SOAK_DURATION_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${SOAK_DURATION_SECONDS}" -lt 1 ]]; then
  echo "SOAK_DURATION_SECONDS must be an integer >= 1"
  exit 1
fi
if ! [[ "${SOAK_INTERVAL_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${SOAK_INTERVAL_SECONDS}" -lt 1 ]]; then
  echo "SOAK_INTERVAL_SECONDS must be an integer >= 1"
  exit 1
fi
if ! [[ "${SOAK_PROBE_RUN_COUNT}" =~ ^[0-9]+$ ]] || [[ "${SOAK_PROBE_RUN_COUNT}" -lt 1 ]]; then
  echo "SOAK_PROBE_RUN_COUNT must be an integer >= 1"
  exit 1
fi
if ! [[ "${SOAK_PROBE_WORKERS}" =~ ^[0-9]+$ ]] || [[ "${SOAK_PROBE_WORKERS}" -lt 1 ]]; then
  echo "SOAK_PROBE_WORKERS must be an integer >= 1"
  exit 1
fi
if ! [[ "${SOAK_MAX_FAILED_RUN_DELTA}" =~ ^-?[0-9]+$ ]]; then
  echo "SOAK_MAX_FAILED_RUN_DELTA must be an integer"
  exit 1
fi

mkdir -p "${REPORT_DIR}"
stamp="$(date -u +"%Y%m%dT%H%M%SZ")"
samples_path="${REPORT_DIR}/${stamp}-tst2-soak-samples.jsonl"
probe_log_path="${REPORT_DIR}/${stamp}-tst2-soak-probe.log"
summary_path="${REPORT_DIR}/${stamp}-tst2-soak-summary.md"

wait_http_ok() {
  local url="$1"
  local max_try="${2:-45}"
  local header="${3:-}"

  for _ in $(seq 1 "${max_try}"); do
    if [[ -n "${header}" ]]; then
      if curl -fsS "${url}" -H "${header}" >/dev/null 2>&1; then
        return 0
      fi
    else
      if curl -fsS "${url}" >/dev/null 2>&1; then
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

if [[ "${SOAK_SKIP_SERVICE_START}" != "true" ]]; then
  if ! service_running "action-layer"; then
    bash "${ROOT_DIR}/scripts/stationctl.sh" start action-layer >/dev/null
    STARTED_ACTION_LAYER=1
  fi
  wait_http_ok "${ACTION_URL}/healthz" 45

  if ! service_running "control-center"; then
    WHERECODE_RELOAD=false bash "${ROOT_DIR}/scripts/stationctl.sh" start control-center >/dev/null
    STARTED_CONTROL_CENTER=1
  fi
  wait_http_ok "${CONTROL_URL}/healthz" 45
  wait_http_ok "${CONTROL_URL}/action-layer/health" 45 "X-WhereCode-Token: ${AUTH_TOKEN}"
fi

total_rounds=$(( (SOAK_DURATION_SECONDS + SOAK_INTERVAL_SECONDS - 1) / SOAK_INTERVAL_SECONDS ))
if [[ "${total_rounds}" -lt 1 ]]; then
  total_rounds=1
fi

echo "tst2 soak start: rounds=${total_rounds} interval=${SOAK_INTERVAL_SECONDS}s duration=${SOAK_DURATION_SECONDS}s"
echo "samples: ${samples_path}"
echo "probe_log: ${probe_log_path}"
echo "summary: ${summary_path}"

for round in $(seq 1 "${total_rounds}"); do
  sampled_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  probe_status="skipped"
  probe_summary=""

  if [[ "${SOAK_RUN_PROBE_EACH_ROUND}" == "true" ]]; then
    if probe_output="$(WHERECODE_TOKEN="${AUTH_TOKEN}" PROBE_STRICT=true bash "${ROOT_DIR}/scripts/v3_parallel_probe.sh" "${CONTROL_URL}" "${SOAK_PROBE_RUN_COUNT}" "${SOAK_PROBE_WORKERS}" 2>&1)"; then
      probe_status="passed"
      probe_summary="$(printf '%s\n' "${probe_output}" | tail -n 1)"
      printf '[%s][round=%s] %s\n' "${sampled_at}" "${round}" "${probe_output}" >>"${probe_log_path}"
    else
      probe_status="failed"
      probe_summary="parallel probe failed"
      printf '[%s][round=%s][failed] %s\n' "${sampled_at}" "${round}" "${probe_output:-}" >>"${probe_log_path}"
      echo "round ${round}: parallel probe failed"
      exit 1
    fi
  fi

  workflow_json="$(curl -fsS "${CONTROL_URL}/metrics/workflows" -H "X-WhereCode-Token: ${AUTH_TOKEN}")"
  summary_json="$(curl -fsS "${CONTROL_URL}/metrics/summary" -H "X-WhereCode-Token: ${AUTH_TOKEN}")"

  python3 - "${samples_path}" "${sampled_at}" "${round}" "${probe_status}" "${probe_summary}" "${workflow_json}" "${summary_json}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
sampled_at = sys.argv[2]
round_no = int(sys.argv[3])
probe_status = sys.argv[4]
probe_summary = sys.argv[5]
workflow = json.loads(sys.argv[6])
summary = json.loads(sys.argv[7])

run_status_counts = workflow.get("run_status_counts", {})
if not isinstance(run_status_counts, dict):
    run_status_counts = {}

payload = {
    "sampled_at": sampled_at,
    "round": round_no,
    "probe_status": probe_status,
    "probe_summary": probe_summary,
    "total_runs": int(workflow.get("total_runs", 0)),
    "total_workitems": int(workflow.get("total_workitems", 0)),
    "failed_run_count": int(run_status_counts.get("failed", 0)),
    "blocked_run_count": int(run_status_counts.get("blocked", 0)),
    "waiting_approval_count": int(summary.get("waiting_approval_count", 0)),
    "in_flight_command_count": int(summary.get("in_flight_command_count", 0)),
    "total_commands": int(summary.get("total_commands", 0)),
    "failed_command_count": int(summary.get("failed_count", 0)),
}

with path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
PY

  echo "round ${round}/${total_rounds} sampled_at=${sampled_at} probe=${probe_status}"
  if [[ "${round}" -lt "${total_rounds}" ]]; then
    sleep "${SOAK_INTERVAL_SECONDS}"
  fi
done

python3 - "${samples_path}" "${summary_path}" "${SOAK_DURATION_SECONDS}" "${SOAK_INTERVAL_SECONDS}" "${SOAK_PROBE_RUN_COUNT}" "${SOAK_PROBE_WORKERS}" "${SOAK_MAX_FAILED_RUN_DELTA}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

samples_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
duration_seconds = int(sys.argv[3])
interval_seconds = int(sys.argv[4])
probe_run_count = int(sys.argv[5])
probe_workers = int(sys.argv[6])
max_failed_delta = int(sys.argv[7])

rows: list[dict[str, object]] = []
for line in samples_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    rows.append(json.loads(line))

if not rows:
    raise SystemExit("no soak samples written")

first = rows[0]
last = rows[-1]
failed_delta = int(last["failed_run_count"]) - int(first["failed_run_count"])
blocked_peak = max(int(item["blocked_run_count"]) for item in rows)
in_flight_peak = max(int(item["in_flight_command_count"]) for item in rows)
waiting_peak = max(int(item["waiting_approval_count"]) for item in rows)
probe_failed = sum(1 for item in rows if item.get("probe_status") == "failed")
probe_passed = sum(1 for item in rows if item.get("probe_status") == "passed")
guard_passed = failed_delta <= max_failed_delta

lines: list[str] = []
lines.append(f"# TST2 Soak Summary ({last['sampled_at'][:10]})")
lines.append("")
lines.append(f"- samples_file: `{samples_path}`")
lines.append(f"- rounds: `{len(rows)}`")
lines.append(f"- soak_duration_seconds: `{duration_seconds}`")
lines.append(f"- soak_interval_seconds: `{interval_seconds}`")
lines.append(f"- probe_each_round_runs: `{probe_run_count}`")
lines.append(f"- probe_workers: `{probe_workers}`")
lines.append("")
lines.append("## Drift metrics")
lines.append("")
lines.append(f"- failed_run_count_start: `{first['failed_run_count']}`")
lines.append(f"- failed_run_count_end: `{last['failed_run_count']}`")
lines.append(f"- failed_run_count_delta: `{failed_delta}`")
lines.append(f"- blocked_run_count_peak: `{blocked_peak}`")
lines.append(f"- in_flight_command_count_peak: `{in_flight_peak}`")
lines.append(f"- waiting_approval_count_peak: `{waiting_peak}`")
lines.append("")
lines.append("## Probe stability")
lines.append("")
lines.append(f"- probe_passed_rounds: `{probe_passed}`")
lines.append(f"- probe_failed_rounds: `{probe_failed}`")
lines.append("")
lines.append("## Guard")
lines.append("")
lines.append(f"- max_allowed_failed_run_delta: `{max_failed_delta}`")
lines.append(f"- guard_passed: `{str(guard_passed).lower()}`")

summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

guard_passed="$(grep -E '^- guard_passed:' "${summary_path}" | head -n 1 | sed -E 's/.*`([^`]*)`.*/\1/')"
if [[ -z "${guard_passed}" ]]; then
  guard_passed="false"
fi

echo "tst2 soak summary generated: ${summary_path}"

if [[ "${SOAK_FAIL_ON_FAILED_DELTA}" == "true" && "${guard_passed}" != "true" ]]; then
  echo "tst2 soak guard failed"
  exit 1
fi
