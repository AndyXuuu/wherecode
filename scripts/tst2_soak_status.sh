#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${SOAK_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
SAMPLES_FILE="${SOAK_SAMPLES_FILE:-}"
EXPECTED_INTERVAL_SECONDS="${SOAK_INTERVAL_SECONDS:-300}"
MAX_STALENESS_SECONDS="${SOAK_MAX_STALENESS_SECONDS:-900}"
MAX_FAILED_RUN_DELTA="${SOAK_MAX_FAILED_RUN_DELTA:-0}"
STRICT_MODE=false

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_soak_status.sh [--samples-file <path>] [--strict]

Options:
  --samples-file <path>   Read a specific soak samples jsonl file.
  --strict                Exit non-zero if stale or failed_run_delta exceeds threshold.

Env:
  SOAK_REPORT_DIR                 default: docs/ops_reports
  SOAK_INTERVAL_SECONDS           default: 300
  SOAK_MAX_STALENESS_SECONDS      default: 900
  SOAK_MAX_FAILED_RUN_DELTA       default: 0
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --samples-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --samples-file"
        exit 1
      fi
      SAMPLES_FILE="$1"
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

if [[ -z "${SAMPLES_FILE}" ]]; then
  latest="$(ls -1t "${REPORT_DIR}"/*-tst2-soak-samples.jsonl 2>/dev/null | head -n 1 || true)"
  if [[ -z "${latest}" ]]; then
    echo '{"error":"no_soak_samples_file_found"}'
    exit 2
  fi
  SAMPLES_FILE="${latest}"
fi

if [[ ! -f "${SAMPLES_FILE}" ]]; then
  echo "{\"error\":\"samples_file_not_found\",\"samples_file\":\"${SAMPLES_FILE}\"}"
  exit 2
fi

status_json="$(python3 - "${SAMPLES_FILE}" "${EXPECTED_INTERVAL_SECONDS}" "${MAX_STALENESS_SECONDS}" "${MAX_FAILED_RUN_DELTA}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

samples_file = Path(sys.argv[1])
expected_interval = int(sys.argv[2])
max_staleness = int(sys.argv[3])
max_failed_delta = int(sys.argv[4])

rows: list[dict[str, object]] = []
for line in samples_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    rows.append(json.loads(line))

if not rows:
    print(json.dumps({"error": "empty_samples_file", "samples_file": str(samples_file)}))
    raise SystemExit(3)

def parse_iso_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

first = rows[0]
last = rows[-1]
first_ts = parse_iso_utc(str(first["sampled_at"]))
last_ts = parse_iso_utc(str(last["sampled_at"]))
now_ts = datetime.now(timezone.utc)

failed_start = int(first.get("failed_run_count", 0))
failed_end = int(last.get("failed_run_count", 0))
failed_delta = failed_end - failed_start
blocked_peak = max(int(item.get("blocked_run_count", 0)) for item in rows)
in_flight_peak = max(int(item.get("in_flight_command_count", 0)) for item in rows)
waiting_peak = max(int(item.get("waiting_approval_count", 0)) for item in rows)
probe_passed = sum(1 for item in rows if str(item.get("probe_status")) == "passed")
probe_failed = sum(1 for item in rows if str(item.get("probe_status")) == "failed")
age_seconds = int((now_ts - last_ts).total_seconds())
expected_next_by = last_ts.timestamp() + expected_interval
stale = age_seconds > max_staleness
guard_drift_passed = failed_delta <= max_failed_delta
guard_passed = guard_drift_passed and not stale

payload = {
    "samples_file": str(samples_file),
    "samples_total": len(rows),
    "first_sampled_at": first["sampled_at"],
    "last_sampled_at": last["sampled_at"],
    "latest_round": int(last.get("round", len(rows))),
    "failed_run_count_start": failed_start,
    "failed_run_count_end": failed_end,
    "failed_run_count_delta": failed_delta,
    "blocked_run_count_peak": blocked_peak,
    "in_flight_command_count_peak": in_flight_peak,
    "waiting_approval_count_peak": waiting_peak,
    "probe_passed_rounds": probe_passed,
    "probe_failed_rounds": probe_failed,
    "last_sample_age_seconds": age_seconds,
    "expected_interval_seconds": expected_interval,
    "max_staleness_seconds": max_staleness,
    "max_failed_run_delta": max_failed_delta,
    "stale": stale,
    "guard_drift_passed": guard_drift_passed,
    "guard_passed": guard_passed,
    "summary": (
        f"round={int(last.get('round', len(rows)))} "
        f"failed_delta={failed_delta} "
        f"stale={str(stale).lower()} "
        f"probe_failed={probe_failed}"
    ),
}
print(json.dumps(payload, ensure_ascii=False))
PY
)"

echo "${status_json}"

if [[ "${STRICT_MODE}" == "true" ]]; then
  strict_guard="$(python3 - <<'PY' "${status_json}"
import json
import sys
payload = json.loads(sys.argv[1])
print("true" if bool(payload.get("guard_passed")) else "false")
PY
)"
  if [[ "${strict_guard}" != "true" ]]; then
    exit 1
  fi
fi
