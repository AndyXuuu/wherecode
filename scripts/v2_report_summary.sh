#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBPROJECT_KEY="stock-sentiment"
LATEST_PATH=""
LATEST_PATH_EXPLICIT="false"
REPORT_PATH=""
REPORT_ID=""
RUN_ID=""
JSON_OUTPUT="false"
COMPACT_OUTPUT="false"
MAX_ACTIONS="3"
MIN_SCORE="0"
ACTION_TYPE=""
API_MODE="false"
CONTROL_URL="${WHERECODE_CONTROL_URL:-http://127.0.0.1:8000}"
TOKEN="${WHERECODE_TOKEN:-change-me}"
DRY_RUN="false"

usage() {
  cat <<'EOF_USAGE'
Usage:
  bash scripts/v2_report_summary.sh [subproject_key] [options]

Options:
  --subproject <key>     default: stock-sentiment
  --latest <path>        default: docs/v2_reports/latest_<subproject>_v2_run.json
  --report <path>        explicit report file (supports latest pointer file too)
  --report-id <id>       locate report by report id (report file stem)
  --run-id <id>          locate report by workflow run id (outputs.workflow_run_id)
  --json                 print summary as json
  --compact              print compact mobile summary
  --max-actions <n>      limit prioritized actions (default: 3)
  --min-score <n>        filter actions by score threshold [0,100]
  --action-type <type>   filter actions by type (`rerun|validate|dependency-check|other`, csv supported)
  --api                  query Control Center API instead of local report file
  --control-url <url>    API base url (default: WHERECODE_CONTROL_URL or http://127.0.0.1:8000)
  --token <token>        API auth token for X-WhereCode-Token (default: WHERECODE_TOKEN or change-me)
  --dry-run              print resolved target path only
  -h, --help
EOF_USAGE
}

if [[ $# -gt 0 && "${1:-}" != -* ]]; then
  SUBPROJECT_KEY="${1:-}"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subproject)
      SUBPROJECT_KEY="${2:-}"
      shift
      ;;
    --latest)
      LATEST_PATH="${2:-}"
      LATEST_PATH_EXPLICIT="true"
      shift
      ;;
    --report)
      REPORT_PATH="${2:-}"
      shift
      ;;
    --report-id)
      REPORT_ID="${2:-}"
      shift
      ;;
    --run-id)
      RUN_ID="${2:-}"
      shift
      ;;
    --json)
      JSON_OUTPUT="true"
      ;;
    --compact)
      COMPACT_OUTPUT="true"
      ;;
    --max-actions)
      MAX_ACTIONS="${2:-}"
      shift
      ;;
    --min-score)
      MIN_SCORE="${2:-}"
      shift
      ;;
    --action-type)
      ACTION_TYPE="${2:-}"
      shift
      ;;
    --api)
      API_MODE="true"
      ;;
    --control-url)
      CONTROL_URL="${2:-}"
      shift
      ;;
    --token)
      TOKEN="${2:-}"
      shift
      ;;
    --dry-run)
      DRY_RUN="true"
      ;;
    -h|--help|help)
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

if [[ -z "${LATEST_PATH}" ]]; then
  LATEST_PATH="${ROOT_DIR}/docs/v2_reports/latest_${SUBPROJECT_KEY}_v2_run.json"
fi

target_input="${REPORT_PATH:-${LATEST_PATH}}"
if [[ "${DRY_RUN}" == "true" ]]; then
  if [[ "${API_MODE}" == "true" ]]; then
    echo "[dry-run] api=true control_url=${CONTROL_URL%/} subproject=${SUBPROJECT_KEY} report_id=${REPORT_ID} run_id=${RUN_ID}"
  else
    echo "[dry-run] target=${target_input} report_id=${REPORT_ID} run_id=${RUN_ID}"
  fi
  exit 0
fi

if [[ "${API_MODE}" == "true" ]]; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "v2_report_summary failed: curl not found"
    exit 1
  fi

  endpoint="${CONTROL_URL%/}/reports/v2/summary"
  body_file="$(mktemp)"
  curl_args=(
    -sS
    -o "${body_file}"
    -w "%{http_code}"
    -G
    -H "X-WhereCode-Token: ${TOKEN}"
    --data-urlencode "compact=${COMPACT_OUTPUT}"
    --data-urlencode "max_actions=${MAX_ACTIONS}"
    --data-urlencode "min_score=${MIN_SCORE}"
  )
  if [[ -n "${REPORT_ID}" ]]; then
    curl_args+=(--data-urlencode "report_id=${REPORT_ID}")
  fi
  if [[ -n "${RUN_ID}" ]]; then
    curl_args+=(--data-urlencode "run_id=${RUN_ID}")
  fi
  if [[ -n "${ACTION_TYPE}" ]]; then
    curl_args+=(--data-urlencode "action_type=${ACTION_TYPE}")
  fi
  if [[ -n "${REPORT_ID}" || -n "${RUN_ID}" ]]; then
    :
  elif [[ -n "${REPORT_PATH}" ]]; then
    curl_args+=(--data-urlencode "report_path=${REPORT_PATH}")
  elif [[ "${LATEST_PATH_EXPLICIT}" == "true" ]]; then
    curl_args+=(--data-urlencode "latest_path=${LATEST_PATH}")
  else
    curl_args+=(--data-urlencode "subproject=${SUBPROJECT_KEY}")
  fi

  http_code="$(curl "${curl_args[@]}" "${endpoint}")"
  if [[ "${http_code}" != "200" ]]; then
    echo "v2_report_summary failed: api request returned http ${http_code}"
    cat "${body_file}"
    rm -f "${body_file}"
    exit 1
  fi

  if [[ "${JSON_OUTPUT}" == "true" ]]; then
    cat "${body_file}"
    rm -f "${body_file}"
    exit 0
  fi

  python3 - "${body_file}" "${COMPACT_OUTPUT}" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

summary = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
compact_output = sys.argv[2].strip().lower() == "true"

compact = summary.get("compact") or {}
prioritized_actions = summary.get("prioritized_actions") or []
retry_hints = summary.get("retry_hints") or []
next_commands = summary.get("next_commands") or []

if compact_output:
    print("v2_report_compact")
    print(f"  status_line: {compact.get('status_line', '')}")
    print(f"  risk_level: {compact.get('risk_level', '')}")
    print(f"  action_required: {str(compact.get('action_required', False)).lower()}")
    print(f"  alert_priority: {compact.get('alert_priority', '')}")
    print(f"  decision: {compact.get('decision', '')}")
    print(f"  primary_action_id: {compact.get('primary_action_id', '')}")
    print(f"  top_retry_hint: {compact.get('top_retry_hint', '')}")
    print(f"  top_next_command: {compact.get('top_next_command', '')}")
    print(f"  prioritized_actions_count: {len(prioritized_actions)}")
    for item in prioritized_actions:
        print(
            f"    {item.get('priority', '')}. [{item.get('action_type', '')}] {item.get('command', '')} "
            f"(action_id: {item.get('action_id', '')}, score: {item.get('score', '')}, "
            f"runbook: {item.get('runbook_ref', '')}, auto: {str(item.get('can_auto_execute', False)).lower()}, "
            f"confirm: {str(item.get('requires_confirmation', True)).lower()}, "
            f"cost: {item.get('estimated_cost', '')}, reason: {item.get('reason', '')})"
        )
    sys.exit(0)

print("v2_report_summary")
print(f"  source_input: {summary.get('source_input', '')}")
if summary.get("latest_pointer"):
    print(f"  latest_pointer: {summary.get('latest_pointer', '')}")
print(f"  report_path: {summary.get('report_path', '')}")
print(f"  report_id: {summary.get('report_id', '')}")
print(f"  captured_at: {summary.get('captured_at', '')}")
print(f"  subproject: {summary.get('subproject_key', '')}")
print(f"  mode: {summary.get('mode', '')}")
print(f"  final_status: {summary.get('final_status', '')}")
print("  failure_taxonomy:")
taxonomy = summary.get("failure_taxonomy") or {}
print(f"    code: {taxonomy.get('code', '')}")
print(f"    stage: {taxonomy.get('stage', '')}")
print(f"    severity: {taxonomy.get('severity', '')}")
print(f"    reason: {taxonomy.get('reason', '')}")
print(f"  retry_hints_count: {len(retry_hints)}")
for idx, hint in enumerate(retry_hints, start=1):
    print(f"    {idx}. {hint}")
print(f"  next_commands_count: {len(next_commands)}")
for idx, command in enumerate(next_commands, start=1):
    print(f"    {idx}. {command}")
print(f"  primary_action: {summary.get('primary_action')}")
print(f"  prioritized_actions_count: {len(prioritized_actions)}")
for item in prioritized_actions:
    print(
        f"    {item.get('priority', '')}. [{item.get('action_type', '')}] {item.get('command', '')} "
        f"(action_id: {item.get('action_id', '')}, score: {item.get('score', '')}, "
        f"runbook: {item.get('runbook_ref', '')}, auto: {str(item.get('can_auto_execute', False)).lower()}, "
        f"confirm: {str(item.get('requires_confirmation', True)).lower()}, "
        f"cost: {item.get('estimated_cost', '')}, reason: {item.get('reason', '')})"
    )
PY
  rm -f "${body_file}"
  exit 0
fi

python3 - "${target_input}" "${JSON_OUTPUT}" "${COMPACT_OUTPUT}" "${MAX_ACTIONS}" "${MIN_SCORE}" "${ACTION_TYPE}" "${REPORT_ID}" "${RUN_ID}" <<'PY'
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any

target_input = Path(sys.argv[1]).resolve()
json_output = sys.argv[2].strip().lower() == "true"
compact_output = sys.argv[3].strip().lower() == "true"
try:
    max_actions = int(sys.argv[4])
except ValueError:
    max_actions = 3
max_actions = max(1, min(max_actions, 10))
try:
    min_score = int(sys.argv[5])
except ValueError:
    min_score = 0
min_score = max(0, min(min_score, 100))
action_type_filter = {
    item.strip().lower()
    for item in str(sys.argv[6] if len(sys.argv) > 6 else "").split(",")
    if item.strip()
}
report_id = str(sys.argv[7] if len(sys.argv) > 7 else "").strip()
run_id = str(sys.argv[8] if len(sys.argv) > 8 else "").strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_report_payload(input_path: Path) -> tuple[Path, dict[str, Any], Path | None]:
    payload = read_json(input_path)
    report_path_value = str(payload.get("report_path") or "").strip()
    if report_path_value:
        candidate = Path(report_path_value)
        if not candidate.is_absolute():
            candidate = (input_path.parent / candidate).resolve()
        if candidate.exists():
            return candidate, read_json(candidate), input_path
    return input_path, payload, None


def resolve_report_by_run_id(search_dir: Path, workflow_run_id: str) -> Path:
    if not search_dir.exists():
        raise FileNotFoundError(f"v2 report directory not found: {search_dir}")
    candidates = sorted(search_dir.glob("*-v2-run.json"), key=lambda p: p.name, reverse=True)
    for candidate in candidates:
        try:
            payload = read_json(candidate)
        except Exception:
            continue
        outputs = payload.get("outputs") or {}
        run = payload.get("run") or {}
        candidate_run_id = str(
            outputs.get("workflow_run_id") or run.get("workflow_run_id") or ""
        ).strip()
        if candidate_run_id and candidate_run_id == workflow_run_id:
            return candidate
    raise FileNotFoundError(f"v2 report not found for run_id: {workflow_run_id}")


if run_id:
    target_input = resolve_report_by_run_id(target_input.parent, run_id).resolve()
elif report_id:
    target_input = (target_input.parent / f"{report_id}.json").resolve()

if not target_input.exists():
    print(f"v2_report_summary failed: file not found: {target_input}")
    sys.exit(1)

report_path, report_payload, latest_pointer = pick_report_payload(target_input)
run = report_payload.get("run") or {}
diagnosis = report_payload.get("diagnosis") or {}
taxonomy = diagnosis.get("failure_taxonomy") or {}

summary = {
    "source_input": str(target_input),
    "latest_pointer": str(latest_pointer) if latest_pointer else "",
    "report_path": str(report_path),
    "report_id": report_path.stem,
    "captured_at": str(report_payload.get("captured_at") or ""),
    "subproject_key": str(run.get("subproject_key") or ""),
    "mode": str(run.get("mode") or ""),
    "final_status": str(run.get("final_status") or ""),
    "failure_taxonomy": {
        "code": str(taxonomy.get("code") or ""),
        "stage": str(taxonomy.get("stage") or ""),
        "severity": str(taxonomy.get("severity") or ""),
        "reason": str(taxonomy.get("reason") or ""),
    },
    "retry_hints": [
        str(item).strip() for item in (diagnosis.get("retry_hints") or []) if str(item).strip()
    ],
    "next_commands": [
        str(item).strip()
        for item in (diagnosis.get("next_commands") or [])
        if str(item).strip()
    ],
}
retry_hints = summary["retry_hints"]
next_commands = summary["next_commands"]


def resolve_risk_level(final_status: str, severity: str) -> str:
    status = final_status.strip().lower()
    sev = severity.strip().lower()
    if status in {"success", "succeeded"}:
        return "low"
    if sev in {"critical", "high"}:
        return "high"
    if status in {"failed", "error"}:
        return "high"
    if status == "canceled":
        return "medium"
    if sev == "medium":
        return "medium"
    return "low"


def resolve_alert_priority(final_status: str, severity: str, action_required: bool) -> str:
    status = final_status.strip().lower()
    sev = severity.strip().lower()
    if status in {"failed", "error"} and sev == "critical":
        return "P0"
    if status in {"failed", "error"} and sev in {"high", "critical"}:
        return "P1"
    if status in {"failed", "error", "canceled"} or sev == "medium":
        return "P2"
    if action_required:
        return "P2"
    return "P3"


def resolve_decision(action_required: bool, alert_priority: str) -> str:
    if not action_required:
        return "observe"
    if alert_priority in {"P0", "P1"}:
        return "act_now"
    return "review_and_run"


def action_base_score(alert_priority: str) -> int:
    if alert_priority == "P0":
        return 100
    if alert_priority == "P1":
        return 85
    if alert_priority == "P2":
        return 65
    return 40


def classify_action_type(command: str) -> str:
    lowered = command.lower()
    if "v2-replay" in lowered or "v2-run" in lowered:
        return "rerun"
    if "check_all" in lowered or "v2_gate" in lowered:
        return "validate"
    if "orchestrate-policy" in lowered:
        return "dependency-check"
    return "other"


def resolve_runbook_ref(action_type: str) -> str:
    if action_type == "rerun":
        return "ops://v2-replay"
    if action_type == "validate":
        return "ops://check-all-v2"
    if action_type == "dependency-check":
        return "ops://orchestrate-policy"
    return "ops://manual-review"


def resolve_estimated_cost(action_type: str) -> str:
    if action_type in {"validate", "dependency-check"}:
        return "low"
    if action_type == "rerun":
        return "medium"
    return "high"


taxonomy_info = summary["failure_taxonomy"]
risk_level = resolve_risk_level(summary["final_status"], taxonomy_info["severity"])
action_required = summary["final_status"].strip().lower() not in {"success", "succeeded"}
alert_priority = resolve_alert_priority(
    summary["final_status"], taxonomy_info["severity"], action_required
)
decision = resolve_decision(action_required, alert_priority)
status_line = (
    f"{summary['subproject_key'] or 'subproject'} "
    f"{summary['mode'] or 'run'} "
    f"{summary['final_status'] or 'unknown'} "
    f"[{taxonomy_info['code'] or 'unknown'}]"
)
base_score = action_base_score(alert_priority)

suggested_actions: list[dict[str, str | int | bool]] = []
for index, command in enumerate(next_commands, start=1):
    reason = (
        retry_hints[index - 1]
        if index - 1 < len(retry_hints)
        else (taxonomy_info["reason"] or "recommended follow-up action")
    )
    action_type = classify_action_type(command)
    score = max(0, base_score - (index - 1) * 7)
    can_auto_execute = action_type in {"validate", "dependency-check"} or (
        action_type == "rerun" and alert_priority in {"P2", "P3"}
    )
    requires_confirmation = alert_priority in {"P0", "P1"} or not can_auto_execute
    action_id = f"{action_type}:{hashlib.sha1(command.encode('utf-8')).hexdigest()[:8]}"
    suggested_actions.append(
        {
            "priority": index,
            "action_id": action_id,
            "action_type": action_type,
            "command": command,
            "reason": reason,
            "score": score,
            "runbook_ref": resolve_runbook_ref(action_type),
            "can_auto_execute": can_auto_execute,
            "requires_confirmation": requires_confirmation,
            "estimated_cost": resolve_estimated_cost(action_type),
        }
    )

prioritized_actions = [
    item
    for item in suggested_actions
    if int(item["score"]) >= min_score
    and (not action_type_filter or str(item["action_type"]) in action_type_filter)
][:max_actions]
for rank, item in enumerate(prioritized_actions, start=1):
    item["priority"] = rank

primary_action = prioritized_actions[0] if prioritized_actions else None
top_retry_hint = str(primary_action["reason"]) if primary_action else (retry_hints[0] if retry_hints else "")
top_next_command = (
    str(primary_action["command"]) if primary_action else (next_commands[0] if next_commands else "")
)

summary["compact"] = {
    "status_line": status_line.strip(),
    "action_required": action_required,
    "alert_priority": alert_priority,
    "decision": decision,
    "risk_level": risk_level,
    "primary_action_id": str(primary_action["action_id"]) if primary_action else "",
    "top_retry_hint": top_retry_hint,
    "top_next_command": top_next_command,
}
summary["prioritized_actions"] = prioritized_actions
summary["primary_action"] = primary_action

if json_output:
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.exit(0)

if compact_output:
    compact = summary["compact"]
    print("v2_report_compact")
    print(f"  status_line: {compact['status_line']}")
    print(f"  risk_level: {compact['risk_level']}")
    print(f"  action_required: {str(compact['action_required']).lower()}")
    print(f"  alert_priority: {compact['alert_priority']}")
    print(f"  decision: {compact['decision']}")
    print(f"  primary_action_id: {compact['primary_action_id']}")
    print(f"  top_retry_hint: {compact['top_retry_hint']}")
    print(f"  top_next_command: {compact['top_next_command']}")
    print(f"  prioritized_actions_count: {len(prioritized_actions)}")
    for item in prioritized_actions:
        print(
            f"    {item['priority']}. [{item['action_type']}] {item['command']} "
            f"(action_id: {item['action_id']}, score: {item['score']}, runbook: {item['runbook_ref']}, "
            f"auto: {str(item['can_auto_execute']).lower()}, confirm: {str(item['requires_confirmation']).lower()}, "
            f"cost: {item['estimated_cost']}, reason: {item['reason']})"
        )
    sys.exit(0)

print("v2_report_summary")
print(f"  source_input: {summary['source_input']}")
if summary["latest_pointer"]:
    print(f"  latest_pointer: {summary['latest_pointer']}")
print(f"  report_path: {summary['report_path']}")
print(f"  report_id: {summary['report_id']}")
print(f"  captured_at: {summary['captured_at']}")
print(f"  subproject: {summary['subproject_key']}")
print(f"  mode: {summary['mode']}")
print(f"  final_status: {summary['final_status']}")
print("  failure_taxonomy:")
print(f"    code: {summary['failure_taxonomy']['code']}")
print(f"    stage: {summary['failure_taxonomy']['stage']}")
print(f"    severity: {summary['failure_taxonomy']['severity']}")
print(f"    reason: {summary['failure_taxonomy']['reason']}")
print(f"  retry_hints_count: {len(retry_hints)}")
for idx, hint in enumerate(retry_hints, start=1):
    print(f"    {idx}. {hint}")
print(f"  next_commands_count: {len(next_commands)}")
for idx, command in enumerate(next_commands, start=1):
    print(f"    {idx}. {command}")
print(f"  primary_action: {summary['primary_action']}")
print(f"  prioritized_actions_count: {len(prioritized_actions)}")
for item in prioritized_actions:
    print(
        f"    {item['priority']}. [{item['action_type']}] {item['command']} "
        f"(action_id: {item['action_id']}, score: {item['score']}, runbook: {item['runbook_ref']}, "
        f"auto: {str(item['can_auto_execute']).lower()}, confirm: {str(item['requires_confirmation']).lower()}, "
        f"cost: {item['estimated_cost']}, reason: {item['reason']})"
    )
PY
