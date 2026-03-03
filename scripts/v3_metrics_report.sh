#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_URL="${1:-http://127.0.0.1:8000}"
ACTION_URL="${2:-http://127.0.0.1:8100}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
REPORT_DIR="${METRICS_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
SNAPSHOT_PATH="${METRICS_SNAPSHOT_PATH:-${REPORT_DIR}/latest_workflow_metrics.json}"
METRICS_SKIP_SERVICE_START="${METRICS_SKIP_SERVICE_START:-false}"
METRICS_FAIL_ON_FAILED_DELTA="${METRICS_FAIL_ON_FAILED_DELTA:-false}"
STARTED_CONTROL_CENTER=0
STARTED_ACTION_LAYER=0

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

mkdir -p "${REPORT_DIR}"
tmp_dir="$(mktemp -d)"
workflow_json="${tmp_dir}/workflow.json"
summary_json="${tmp_dir}/summary.json"
meta_json="${tmp_dir}/meta.json"

if [[ "${METRICS_SKIP_SERVICE_START}" != "true" ]]; then
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

curl -fsS "${CONTROL_URL}/metrics/workflows" -H "X-WhereCode-Token: ${AUTH_TOKEN}" >"${workflow_json}"
curl -fsS "${CONTROL_URL}/metrics/summary" -H "X-WhereCode-Token: ${AUTH_TOKEN}" >"${summary_json}"

python3 - "${workflow_json}" "${summary_json}" "${SNAPSHOT_PATH}" "${REPORT_DIR}" "${meta_json}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

workflow_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
snapshot_path = Path(sys.argv[3])
report_dir = Path(sys.argv[4])
meta_path = Path(sys.argv[5])

workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
summary = json.loads(summary_path.read_text(encoding="utf-8"))

previous: dict[str, object] = {}
if snapshot_path.exists():
    previous = json.loads(snapshot_path.read_text(encoding="utf-8"))

prev_workflow = previous.get("workflow_metrics", {}) if isinstance(previous, dict) else {}
prev_summary = previous.get("summary_metrics", {}) if isinstance(previous, dict) else {}

timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
report_date = timestamp[:10]
report_file = report_dir / f"{report_date}-workflow-metrics.md"


def int_value(source: dict[str, object], key: str) -> int:
    value = source.get(key, 0)
    return int(value) if isinstance(value, (int, float)) else 0


def delta(source: dict[str, object], previous_source: dict[str, object], key: str) -> int:
    return int_value(source, key) - int_value(previous_source, key)


current_failed_runs = workflow.get("run_status_counts", {}).get("failed", 0)
if not isinstance(current_failed_runs, int):
    current_failed_runs = 0
previous_failed_runs = 0
if isinstance(prev_workflow, dict):
    prev_counts = prev_workflow.get("run_status_counts", {})
    if isinstance(prev_counts, dict):
        prev_failed_raw = prev_counts.get("failed", 0)
        if isinstance(prev_failed_raw, int):
            previous_failed_runs = prev_failed_raw
failed_run_delta = current_failed_runs - previous_failed_runs

sections: list[str] = []
sections.append(f"# Workflow Metrics Report ({report_date})")
sections.append("")
sections.append(f"- generated_at_utc: `{timestamp}`")
sections.append("")
sections.append("## Workflow totals")
sections.append("")
sections.append("| Metric | Current | Delta vs prev |")
sections.append("| --- | ---: | ---: |")
for key in ("total_runs", "total_workitems", "total_gate_checks", "total_artifacts"):
    sections.append(f"| {key} | {int_value(workflow, key)} | {delta(workflow, prev_workflow if isinstance(prev_workflow, dict) else {}, key)} |")

sections.append("")
sections.append("## Command totals")
sections.append("")
sections.append("| Metric | Current | Delta vs prev |")
sections.append("| --- | ---: | ---: |")
for key in ("total_commands", "in_flight_command_count", "waiting_approval_count", "failed_count", "success_count"):
    sections.append(f"| {key} | {int_value(summary, key)} | {delta(summary, prev_summary if isinstance(prev_summary, dict) else {}, key)} |")

sections.append("")
sections.append("## Run status counts")
sections.append("")
sections.append("| Status | Count |")
sections.append("| --- | ---: |")
run_status_counts = workflow.get("run_status_counts", {})
if isinstance(run_status_counts, dict) and run_status_counts:
    for key in sorted(run_status_counts.keys()):
        value = run_status_counts[key]
        if isinstance(value, int):
            sections.append(f"| {key} | {value} |")
else:
    sections.append("| (empty) | 0 |")

sections.append("")
sections.append("## Notes")
sections.append("")
if failed_run_delta > 0:
    sections.append(f"- failed run count increased by `{failed_run_delta}`; investigate gate/discussion/reflow records.")
elif failed_run_delta < 0:
    sections.append(f"- failed run count decreased by `{abs(failed_run_delta)}`.")
else:
    sections.append("- failed run count unchanged.")

report_file.write_text("\n".join(sections) + "\n", encoding="utf-8")

snapshot_payload = {
    "generated_at_utc": timestamp,
    "workflow_metrics": workflow,
    "summary_metrics": summary,
    "previous_workflow_metrics": prev_workflow if isinstance(prev_workflow, dict) else {},
    "previous_summary_metrics": prev_summary if isinstance(prev_summary, dict) else {},
}
snapshot_path.write_text(
    json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

meta_payload = {
    "report_file": str(report_file),
    "snapshot_file": str(snapshot_path),
    "failed_run_delta": failed_run_delta,
}
meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False), encoding="utf-8")
print(str(report_file))
PY

failed_delta="$(python3 - "${meta_json}" <<'PY'
import json,sys
meta=json.load(open(sys.argv[1], encoding="utf-8"))
print(int(meta.get("failed_run_delta",0)))
PY
)"
report_file="$(python3 - "${meta_json}" <<'PY'
import json,sys
meta=json.load(open(sys.argv[1], encoding="utf-8"))
print(meta.get("report_file",""))
PY
)"

echo "metrics report generated: ${report_file}"

if [[ "${METRICS_FAIL_ON_FAILED_DELTA}" == "true" && "${failed_delta}" -gt 0 ]]; then
  echo "metrics guard failed: failed run count delta is ${failed_delta}"
  exit 1
fi
