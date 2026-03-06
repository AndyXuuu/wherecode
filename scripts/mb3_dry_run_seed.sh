#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_URL="${WHERECODE_CONTROL_URL:-http://127.0.0.1:8000}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"

PROJECT_NAME="${MB3_DRY_RUN_PROJECT_NAME:-mb3-stock-sentiment-$(date -u +%Y%m%d%H%M%S)}"
TASK_TITLE="${MB3_DRY_RUN_TASK_TITLE:-mb3 stock sentiment dry-run task}"
REQUIREMENTS="${MB3_DRY_RUN_REQUIREMENTS:-build stock sentiment pipeline with opinion crawl, sentiment scoring, theme and industry analysis, and risk summary output}"
MODULE_HINTS="${MB3_DRY_RUN_MODULE_HINTS:-crawl,sentiment,theme,industry,risk}"
MAX_MODULES="${MB3_DRY_RUN_MAX_MODULES:-6}"
STRATEGY="${MB3_DRY_RUN_STRATEGY:-balanced}"
EXECUTE="${MB3_DRY_RUN_EXECUTE:-false}"
FORCE_REDECOMPOSE="${MB3_DRY_RUN_FORCE_REDECOMPOSE:-false}"
REQUESTED_BY="${MB3_DRY_RUN_REQUESTED_BY:-mb3-seed}"
CONFIRMED_BY="${MB3_DRY_RUN_CONFIRMED_BY:-owner}"
COMMAND_PREFIX="${MB3_DRY_RUN_COMMAND_PREFIX:-/orchestrate}"

POLL_TIMEOUT_SECONDS="${MB3_DRY_RUN_POLL_TIMEOUT_SECONDS:-120}"
POLL_INTERVAL_SECONDS="${MB3_DRY_RUN_POLL_INTERVAL_SECONDS:-1}"

REPORT_DIR="${MB3_DRY_RUN_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
LATEST_SUMMARY_PATH="${MB3_DRY_RUN_LATEST_SUMMARY_PATH:-${REPORT_DIR}/latest_mb3_dry_run_seed.json}"
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage:
  bash scripts/mb3_dry_run_seed.sh [control_url] [options]

Options:
  --project-name <name>
  --task-title <title>
  --requirements <text>
  --module-hints <csv>
  --max-modules <n>
  --strategy <speed|balanced|safe>
  --execute <true|false>
  --force-redecompose <true|false>
  --requested-by <name>
  --confirmed-by <name>
  --command-prefix <text>
  --poll-timeout <seconds>
  --poll-interval <seconds>
  --report-dir <path>
  --latest-summary <path>
  --dry-run
  -h, --help

Env:
  WHERECODE_TOKEN
  MB3_DRY_RUN_*
EOF
}

POSITIONALS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-name)
      PROJECT_NAME="${2:-}"
      shift
      ;;
    --task-title)
      TASK_TITLE="${2:-}"
      shift
      ;;
    --requirements)
      REQUIREMENTS="${2:-}"
      shift
      ;;
    --module-hints)
      MODULE_HINTS="${2:-}"
      shift
      ;;
    --max-modules)
      MAX_MODULES="${2:-}"
      shift
      ;;
    --strategy)
      STRATEGY="${2:-}"
      shift
      ;;
    --execute)
      EXECUTE="${2:-}"
      shift
      ;;
    --force-redecompose)
      FORCE_REDECOMPOSE="${2:-}"
      shift
      ;;
    --requested-by)
      REQUESTED_BY="${2:-}"
      shift
      ;;
    --confirmed-by)
      CONFIRMED_BY="${2:-}"
      shift
      ;;
    --command-prefix)
      COMMAND_PREFIX="${2:-}"
      shift
      ;;
    --poll-timeout)
      POLL_TIMEOUT_SECONDS="${2:-}"
      shift
      ;;
    --poll-interval)
      POLL_INTERVAL_SECONDS="${2:-}"
      shift
      ;;
    --report-dir)
      REPORT_DIR="${2:-}"
      shift
      ;;
    --latest-summary)
      LATEST_SUMMARY_PATH="${2:-}"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "unknown option: $1"
      usage
      exit 1
      ;;
    *)
      POSITIONALS+=("$1")
      ;;
  esac
  shift
done

if [[ ${#POSITIONALS[@]} -gt 0 ]]; then
  CONTROL_URL="${POSITIONALS[0]}"
fi

if [[ -z "${PROJECT_NAME}" || -z "${TASK_TITLE}" || -z "${REQUIREMENTS}" ]]; then
  echo "project-name/task-title/requirements cannot be empty"
  exit 1
fi

command_text="$(python3 - "${COMMAND_PREFIX}" "${REQUIREMENTS}" "${MODULE_HINTS}" "${MAX_MODULES}" "${STRATEGY}" "${EXECUTE}" "${FORCE_REDECOMPOSE}" "${CONFIRMED_BY}" <<'PY'
from __future__ import annotations

import sys

command_prefix = sys.argv[1].strip()
requirements = sys.argv[2].strip()
module_hints = sys.argv[3].strip()
max_modules = sys.argv[4].strip()
strategy = sys.argv[5].strip()
execute = sys.argv[6].strip()
force_redecompose = sys.argv[7].strip()
confirmed_by = sys.argv[8].strip()

parts = [
    command_prefix,
    requirements,
    f"--module-hints={module_hints}",
    f"--max-modules={max_modules}",
    f"--strategy={strategy}",
    f"--execute={execute}",
    f"--force-redecompose={force_redecompose}",
]
if confirmed_by:
    parts.append(f"--confirmed-by={confirmed_by}")
print(" ".join(item for item in parts if item))
PY
)"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] control_url=${CONTROL_URL}"
  echo "[dry-run] project_name=${PROJECT_NAME}"
  echo "[dry-run] task_title=${TASK_TITLE}"
  echo "[dry-run] command_text=${command_text}"
  echo "[dry-run] requested_by=${REQUESTED_BY}"
  exit 0
fi

AUTH_HEADER="X-WhereCode-Token: ${AUTH_TOKEN}"
JSON_HEADER="Content-Type: application/json"

echo "[1/5] create project"
project_payload="$(python3 - "${PROJECT_NAME}" <<'PY'
from __future__ import annotations

import json
import sys

print(json.dumps({"name": sys.argv[1]}))
PY
)"
project_json="$(curl -fsS -X POST "${CONTROL_URL}/projects" \
  -H "${JSON_HEADER}" \
  -H "${AUTH_HEADER}" \
  -d "${project_payload}")"
project_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${project_json}")"
echo "project_id=${project_id}"

echo "[2/5] create task"
task_payload="$(python3 - "${TASK_TITLE}" <<'PY'
from __future__ import annotations

import json
import sys

print(json.dumps({"title": sys.argv[1]}))
PY
)"
task_json="$(curl -fsS -X POST "${CONTROL_URL}/projects/${project_id}/tasks" \
  -H "${JSON_HEADER}" \
  -H "${AUTH_HEADER}" \
  -d "${task_payload}")"
task_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${task_json}")"
echo "task_id=${task_id}"

echo "[3/5] submit orchestrate command"
command_payload="$(python3 - "${command_text}" "${REQUESTED_BY}" <<'PY'
from __future__ import annotations

import json
import sys

print(json.dumps({"text": sys.argv[1], "requested_by": sys.argv[2]}))
PY
)"
accepted_json="$(curl -fsS -X POST "${CONTROL_URL}/tasks/${task_id}/commands" \
  -H "${JSON_HEADER}" \
  -H "${AUTH_HEADER}" \
  -d "${command_payload}")"
command_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["command_id"])' <<<"${accepted_json}")"
echo "command_id=${command_id}"

echo "[4/5] poll command terminal status"
deadline_epoch="$(( $(date +%s) + POLL_TIMEOUT_SECONDS ))"
terminal_json=""
terminal_status=""
while true; do
  command_json="$(curl -fsS "${CONTROL_URL}/commands/${command_id}" -H "${AUTH_HEADER}")"
  status_value="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"${command_json}")"
  echo "status=${status_value}"
  case "${status_value}" in
    success|failed|canceled)
      terminal_json="${command_json}"
      terminal_status="${status_value}"
      break
      ;;
  esac
  if [[ "$(date +%s)" -ge "${deadline_epoch}" ]]; then
    echo "timeout waiting for command=${command_id} terminal status"
    echo "last_status=${status_value}"
    exit 1
  fi
  sleep "${POLL_INTERVAL_SECONDS}"
done

workflow_run_id="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); meta=payload.get("metadata") or {}; print(meta.get("workflow_run_id",""))' <<<"${terminal_json}")"
orchestration_status="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); meta=payload.get("metadata") or {}; print(meta.get("orchestration_status",""))' <<<"${terminal_json}")"
primary_recovery_action="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); meta=payload.get("metadata") or {}; state=meta.get("workflow_state_latest") or {}; print(state.get("primary_recovery_action",""))' <<<"${terminal_json}")"
workflow_next_action="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); meta=payload.get("metadata") or {}; state=meta.get("workflow_state_latest") or {}; print(state.get("next_action",""))' <<<"${terminal_json}")"

latest_found="false"
latest_orchestration_status=""
latest_next_action=""
latest_primary_recovery_action=""

if [[ -n "${workflow_run_id}" ]]; then
  set +e
  latest_json="$(curl -fsS "${CONTROL_URL}/v3/workflows/runs/${workflow_run_id}/orchestrate/latest" -H "${AUTH_HEADER}" 2>/dev/null)"
  latest_rc=$?
  set -e
  if [[ "${latest_rc}" -eq 0 ]]; then
    latest_found="$(python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("found", False)).lower())' <<<"${latest_json}")"
    latest_orchestration_status="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); record=payload.get("record") or {}; print(record.get("orchestration_status",""))' <<<"${latest_json}")"
    latest_next_action="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); record=payload.get("record") or {}; snap=record.get("telemetry_snapshot") or {}; print(snap.get("next_action_after",""))' <<<"${latest_json}")"
    latest_primary_recovery_action="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); record=payload.get("record") or {}; report=record.get("decision_report") or {}; machine=report.get("machine") or {}; print(machine.get("primary_recovery_action",""))' <<<"${latest_json}")"
  fi
fi

if [[ -z "${primary_recovery_action}" ]]; then
  primary_recovery_action="${latest_primary_recovery_action}"
fi

echo "[5/5] write dry-run summary"
mkdir -p "${REPORT_DIR}"
report_stamp="$(date -u +"%Y%m%dT%H%M%SZ")"
report_path="${REPORT_DIR}/${report_stamp}-mb3-dry-run-seed.json"

python3 - "${report_path}" "${LATEST_SUMMARY_PATH}" "${CONTROL_URL}" "${project_id}" "${task_id}" "${command_id}" "${terminal_status}" "${workflow_run_id}" "${orchestration_status}" "${workflow_next_action}" "${primary_recovery_action}" "${latest_found}" "${latest_orchestration_status}" "${latest_next_action}" "${command_text}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

report_path = Path(sys.argv[1])
latest_summary_path = Path(sys.argv[2])
payload = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "control_url": sys.argv[3],
    "project_id": sys.argv[4],
    "task_id": sys.argv[5],
    "command_id": sys.argv[6],
    "terminal_status": sys.argv[7],
    "workflow_run_id": sys.argv[8],
    "orchestration_status": sys.argv[9],
    "workflow_next_action": sys.argv[10],
    "primary_recovery_action": sys.argv[11],
    "latest_found": sys.argv[12] == "true",
    "latest_orchestration_status": sys.argv[13],
    "latest_next_action": sys.argv[14],
    "command_text": sys.argv[15],
}
report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest_summary_path.parent.mkdir(parents=True, exist_ok=True)
latest_summary_path.write_text(
    json.dumps(
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "report_path": str(report_path),
            **payload,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY

echo "report_written=${report_path}"
echo "latest_summary=${LATEST_SUMMARY_PATH}"
echo "project_id=${project_id}"
echo "task_id=${task_id}"
echo "command_id=${command_id}"
echo "command_status=${terminal_status}"
echo "workflow_run_id=${workflow_run_id}"
echo "orchestration_status=${orchestration_status:-${latest_orchestration_status}}"
echo "primary_recovery_action=${primary_recovery_action}"

if [[ -z "${workflow_run_id}" ]]; then
  echo "mb3 dry-run seed failed: workflow_run_id missing"
  exit 1
fi

if [[ "${terminal_status}" != "success" ]]; then
  echo "mb3 dry-run seed completed with non-success command status; use recovery path."
  echo "recovery_action=${primary_recovery_action:-none}"
fi
