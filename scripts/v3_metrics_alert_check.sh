#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPSHOT_PATH="${1:-${ROOT_DIR}/docs/ops_reports/latest_workflow_metrics.json}"
POLICY_PATH="${2:-${ROOT_DIR}/control_center/metrics_alert_policy.json}"
OUTPUT_DIR="${3:-${ROOT_DIR}/docs/ops_reports}"
EXIT_NONZERO="${METRICS_ALERT_EXIT_NONZERO:-false}"

mkdir -p "${OUTPUT_DIR}"
meta_json="$(mktemp)"

python3 - "${SNAPSHOT_PATH}" "${POLICY_PATH}" "${OUTPUT_DIR}" "${meta_json}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

snapshot_path = Path(sys.argv[1])
policy_path = Path(sys.argv[2])
output_dir = Path(sys.argv[3])
meta_path = Path(sys.argv[4])

if not snapshot_path.exists():
    raise SystemExit(f"snapshot not found: {snapshot_path}")
if not policy_path.exists():
    raise SystemExit(f"policy not found: {policy_path}")

snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
policy = json.loads(policy_path.read_text(encoding="utf-8"))

workflow = snapshot.get("workflow_metrics", {})
summary = snapshot.get("summary_metrics", {})
if not isinstance(workflow, dict):
    workflow = {}
if not isinstance(summary, dict):
    summary = {}

run_status_counts = workflow.get("run_status_counts", {})
if not isinstance(run_status_counts, dict):
    run_status_counts = {}


def metric_value(key: str) -> int:
    if key == "failed_run_count":
        value = run_status_counts.get("failed", 0)
    elif key == "blocked_run_count":
        value = run_status_counts.get("blocked", 0)
    elif key == "waiting_approval_count":
        value = summary.get("waiting_approval_count", 0)
    elif key == "in_flight_command_count":
        value = summary.get("in_flight_command_count", 0)
    elif key == "failed_run_delta":
        previous_failed = 0
        previous = snapshot.get("previous_workflow_metrics", {})
        if isinstance(previous, dict):
            prev_counts = previous.get("run_status_counts", {})
            if isinstance(prev_counts, dict):
                prev_failed_raw = prev_counts.get("failed", 0)
                if isinstance(prev_failed_raw, int):
                    previous_failed = prev_failed_raw
        current_failed = run_status_counts.get("failed", 0)
        if not isinstance(current_failed, int):
            current_failed = 0
        return current_failed - previous_failed
    else:
        value = workflow.get(key, 0)
    return int(value) if isinstance(value, (int, float)) else 0


checks: list[dict[str, object]] = []
for key, threshold in policy.items():
    if not isinstance(key, str) or not isinstance(threshold, (int, float)):
        continue
    if key.endswith("_gt"):
        metric_key = key[: -len("_gt")]
        operator = ">"
        limit = float(threshold)
        current = float(metric_value(metric_key))
        triggered = current > limit
    elif key.endswith("_gte"):
        metric_key = key[: -len("_gte")]
        operator = ">="
        limit = float(threshold)
        current = float(metric_value(metric_key))
        triggered = current >= limit
    else:
        continue
    checks.append(
        {
            "rule": key,
            "metric": metric_key,
            "operator": operator,
            "threshold": limit,
            "current": current,
            "triggered": triggered,
        }
    )

triggered_checks = [item for item in checks if item["triggered"] is True]
generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
ticket_path = ""

if triggered_checks:
    stamp = generated_at.replace(":", "").replace("-", "")
    ticket_path = str(output_dir / f"{stamp}-metrics-alert-ticket.md")
    lines: list[str] = []
    lines.append(f"# Metrics Alert Ticket Draft ({generated_at[:10]})")
    lines.append("")
    lines.append(f"- generated_at_utc: `{generated_at}`")
    lines.append(f"- snapshot: `{snapshot_path}`")
    lines.append("")
    lines.append("## Triggered rules")
    lines.append("")
    lines.append("| Rule | Metric | Current | Threshold |")
    lines.append("| --- | --- | ---: | ---: |")
    for item in triggered_checks:
        threshold_display = int(item["threshold"]) if float(item["threshold"]).is_integer() else item["threshold"]
        current_display = int(item["current"]) if float(item["current"]).is_integer() else item["current"]
        lines.append(
            f"| {item['rule']} | {item['metric']} | {current_display} | {item['operator']} {threshold_display} |"
        )
    lines.append("")
    lines.append("## Suggested actions")
    lines.append("")
    lines.append("1. Check latest gates/discussions for failed or blocked runs.")
    lines.append("2. Validate release approvals queue and in-flight command backlog.")
    lines.append("3. Assign owner and ETA in incident channel.")
    Path(ticket_path).write_text("\n".join(lines) + "\n", encoding="utf-8")

meta = {
    "triggered": bool(triggered_checks),
    "triggered_count": len(triggered_checks),
    "ticket_path": ticket_path,
}
meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False))
PY

triggered="$(python3 - "${meta_json}" <<'PY'
import json,sys
meta=json.load(open(sys.argv[1], encoding="utf-8"))
print("true" if bool(meta.get("triggered")) else "false")
PY
)"
ticket_path="$(python3 - "${meta_json}" <<'PY'
import json,sys
meta=json.load(open(sys.argv[1], encoding="utf-8"))
print(meta.get("ticket_path",""))
PY
)"

if [[ "${triggered}" == "true" ]]; then
  echo "metrics alert triggered"
  if [[ -n "${ticket_path}" ]]; then
    echo "ticket draft: ${ticket_path}"
  fi
  if [[ "${EXIT_NONZERO}" == "true" ]]; then
    exit 1
  fi
  exit 0
fi

echo "metrics alert check passed (no triggered rules)"
