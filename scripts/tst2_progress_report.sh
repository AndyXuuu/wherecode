#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="full"
STRICT_MODE=false
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_progress_report.sh [--profile full|local] [--strict] [gate-options...]

Options:
  --profile <full|local>  TST2 readiness profile (default: full)
  --strict                Exit non-zero when profile gate is not passed

Any extra options are forwarded to:
  bash scripts/v3_milestone_gate.sh --milestone tst2-ready ...
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
    --strict)
      STRICT_MODE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      ;;
  esac
  shift
done

if [[ "${PROFILE}" != "full" && "${PROFILE}" != "local" ]]; then
  echo "unsupported profile: ${PROFILE}"
  exit 1
fi

gate_cmd=(
  bash
  "${ROOT_DIR}/scripts/v3_milestone_gate.sh"
  --milestone
  tst2-ready
  --tst2-profile
  "${PROFILE}"
)
if [[ "${#EXTRA_ARGS[@]}" -gt 0 ]]; then
  gate_cmd+=("${EXTRA_ARGS[@]}")
fi

set +e
gate_output="$("${gate_cmd[@]}" 2>&1)"
gate_rc=$?
set -e
if [[ "${gate_rc}" -ne 0 ]]; then
  echo "${gate_output}"
  exit "${gate_rc}"
fi

result_json="$(python3 - "${PROFILE}" "${gate_output}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

profile = sys.argv[1]
payload = json.loads(sys.argv[2])

required = payload.get("required", {})
observed = payload.get("observed", {})

samples_total = int(observed.get("samples_total", 0) or 0)
samples_required = int(required.get("tst2_min_samples", 0) or 0)
coverage_seconds = int(observed.get("coverage_seconds", 0) or 0)
coverage_required_seconds = int(required.get("tst2_required_coverage_seconds", 0) or 0)
interval_seconds = int(required.get("tst2_interval_seconds", 0) or 0)
duration_seconds = int(required.get("tst2_duration_seconds", 0) or 0)
samples_remaining = max(samples_required - samples_total, 0)
coverage_remaining_seconds = max(coverage_required_seconds - coverage_seconds, 0)

coverage_progress_pct = 0.0
if coverage_required_seconds > 0:
    coverage_progress_pct = round(min(coverage_seconds / coverage_required_seconds, 1.0) * 100, 2)

rounds_from_coverage = 0
if interval_seconds > 0 and coverage_remaining_seconds > 0:
    rounds_from_coverage = (coverage_remaining_seconds + interval_seconds - 1) // interval_seconds
forecast_rounds_remaining = max(samples_remaining, rounds_from_coverage)
forecast_seconds_remaining = max(
    coverage_remaining_seconds,
    forecast_rounds_remaining * interval_seconds if interval_seconds > 0 else 0,
)
forecast_hours_remaining = round(forecast_seconds_remaining / 3600, 2)

projected_ready_at_utc = None
last_sampled_at = observed.get("last_sampled_at")
if isinstance(last_sampled_at, str) and last_sampled_at:
    try:
        last_dt = datetime.fromisoformat(last_sampled_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        projected_ready_at_utc = (last_dt + timedelta(seconds=forecast_seconds_remaining)).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        projected_ready_at_utc = None

report = {
    "profile": profile,
    "passed": bool(payload.get("passed")),
    "status": payload.get("status"),
    "samples_total": samples_total,
    "samples_required": samples_required,
    "samples_remaining": samples_remaining,
    "duration_seconds": duration_seconds,
    "interval_seconds": interval_seconds,
    "coverage_seconds": coverage_seconds,
    "coverage_required_seconds": coverage_required_seconds,
    "coverage_remaining_seconds": coverage_remaining_seconds,
    "coverage_progress_pct": coverage_progress_pct,
    "forecast_rounds_remaining": forecast_rounds_remaining,
    "forecast_seconds_remaining": forecast_seconds_remaining,
    "forecast_hours_remaining": forecast_hours_remaining,
    "projected_ready_at_utc": projected_ready_at_utc,
    "failed_run_count_delta": int(observed.get("failed_run_count_delta", 0) or 0),
    "probe_failed_rounds": int(observed.get("probe_failed_rounds", 0) or 0),
    "rehearsal_overall_passed": bool(observed.get("rehearsal_overall_passed")),
    "rehearsal_checkpoint_guard_passed": bool(observed.get("rehearsal_checkpoint_guard_passed")),
    "missing_checks": payload.get("missing_checks", []),
    "recommended_next_action": payload.get("recommended_next_action"),
    "summary": payload.get("summary"),
}
print(json.dumps(report, ensure_ascii=False))
PY
)"

echo "${result_json}"

if [[ "${STRICT_MODE}" == "true" ]]; then
  passed="$(python3 - "${result_json}" <<'PY'
from __future__ import annotations

import json
import sys

payload = json.loads(sys.argv[1])
print("true" if bool(payload.get("passed")) else "false")
PY
)"
  if [[ "${passed}" != "true" ]]; then
    exit 1
  fi
fi
