#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBPROJECT_KEY="${1:-stock-sentiment}"

REQUIREMENTS=""
MODULE_HINTS="crawl,sentiment,theme,industry,risk"
MAX_MODULES="6"
STRATEGY="balanced"
REQUESTED_BY="go8-full-cycle"
EXECUTE="false"
FORCE_CLEAN="true"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORKFLOW_MODE="test"
WORKFLOW_STATE_PATH=""
WORKFLOW_OPS_LOG_PATH=""
RESET_DEV_STATE="false"

usage() {
  cat <<'EOF_USAGE'
Usage:
  bash scripts/go8_subproject_full_cycle.sh [subproject_key] [options]

Options:
  --requirements <text>            required if no existing evolve.json requirements
  --module-hints <csv>             default: crawl,sentiment,theme,industry,risk
  --max-modules <n>                default: 6
  --strategy <speed|balanced|safe> default: balanced
  --requested-by <name>            default: go8-full-cycle
  --execute <true|false>           default: false
  --force-clean <true|false>       default: true
  --stamp <utc_stamp>              default: now
  --workflow-mode <test|dev>       default: test
  --state-path <path>              default: project/<key>/reports/workflow_state.json
  --ops-log-path <path>            default: project/<key>/reports/<stamp>-workflow-ops.jsonl
  --reset-dev-state <true|false>   default: false
  -h, --help

Flow:
  test mode:
    1) generate subproject scaffold
    2) run local standalone subproject flow
    3) write acceptance summary report
  dev mode:
    - one stage per run (generate -> standalone -> acceptance)
    - stage cursor persisted in workflow_state.json
EOF_USAGE
}

is_true() {
  case "${1:-}" in
    true|TRUE|True|1|yes|YES|Yes) return 0 ;;
    *) return 1 ;;
  esac
}

if [[ "${SUBPROJECT_KEY}" == "-h" || "${SUBPROJECT_KEY}" == "--help" || "${SUBPROJECT_KEY}" == "help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
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
    --requested-by)
      REQUESTED_BY="${2:-}"
      shift
      ;;
    --execute)
      EXECUTE="${2:-}"
      shift
      ;;
    --force-clean)
      FORCE_CLEAN="${2:-true}"
      shift
      ;;
    --stamp)
      STAMP="${2:-${STAMP}}"
      shift
      ;;
    --workflow-mode)
      WORKFLOW_MODE="${2:-${WORKFLOW_MODE}}"
      shift
      ;;
    --state-path)
      WORKFLOW_STATE_PATH="${2:-}"
      shift
      ;;
    --ops-log-path)
      WORKFLOW_OPS_LOG_PATH="${2:-}"
      shift
      ;;
    --reset-dev-state)
      RESET_DEV_STATE="${2:-false}"
      shift
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

SUBPROJECT_DIR="${ROOT_DIR}/project/${SUBPROJECT_KEY}"
CONFIG_PATH="${SUBPROJECT_DIR}/evolve.json"
REPORT_DIR="${SUBPROJECT_DIR}/reports"
LATEST_AUTO_PATH="${REPORT_DIR}/latest_autoevolve.json"
LATEST_FULL_CYCLE_PATH="${REPORT_DIR}/latest_full_cycle.json"
FULL_CYCLE_REPORT_PATH="${REPORT_DIR}/${STAMP}-full-cycle.json"
LATEST_WORKFLOW_STATE_PATH="${REPORT_DIR}/latest_workflow_state.json"
LATEST_WORKFLOW_OPS_PATH="${REPORT_DIR}/latest_workflow_ops.json"
REQUIRED_CODE_FILES=(
  "${SUBPROJECT_DIR}/backend/app/main.py"
  "${SUBPROJECT_DIR}/backend/app/analyzer.py"
  "${SUBPROJECT_DIR}/backend/app/models.py"
  "${SUBPROJECT_DIR}/backend/tests/test_analyzer.py"
  "${SUBPROJECT_DIR}/frontend/index.html"
)

WORKFLOW_MODE="$(echo "${WORKFLOW_MODE}" | tr '[:upper:]' '[:lower:]')"
if [[ "${WORKFLOW_MODE}" != "test" && "${WORKFLOW_MODE}" != "dev" ]]; then
  echo "workflow-mode must be test|dev"
  exit 1
fi

if [[ -z "${WORKFLOW_STATE_PATH}" ]]; then
  WORKFLOW_STATE_PATH="${REPORT_DIR}/workflow_state.json"
fi
if [[ -z "${WORKFLOW_OPS_LOG_PATH}" ]]; then
  WORKFLOW_OPS_LOG_PATH="${REPORT_DIR}/${STAMP}-workflow-ops.jsonl"
fi

mkdir -p "${REPORT_DIR}" "$(dirname "${WORKFLOW_OPS_LOG_PATH}")"

if [[ -z "${REQUIREMENTS}" && -f "${CONFIG_PATH}" ]]; then
  REQUIREMENTS="$({
    python3 - "${CONFIG_PATH}" <<'PY'
import json
import sys
from pathlib import Path

try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    payload = {}
print(str(payload.get("requirements") or "").strip())
PY
  })"
fi

if [[ -z "${REQUIREMENTS}" ]]; then
  echo "requirements is required (pass --requirements or keep it in existing evolve.json)"
  exit 1
fi

log_op() {
  local event stage status command detail artifacts_csv
  event="$1"
  stage="$2"
  status="$3"
  command="$4"
  detail="${5:-}"
  artifacts_csv="${6:-}"
  echo "[go8][${WORKFLOW_MODE}] event=${event} stage=${stage} status=${status}"
  if [[ -n "${command}" ]]; then
    echo "[go8][${WORKFLOW_MODE}] command=${command}"
  fi
  if [[ -n "${artifacts_csv}" ]]; then
    echo "[go8][${WORKFLOW_MODE}] files=${artifacts_csv//||/, }"
  fi
  if [[ -n "${detail}" ]]; then
    echo "[go8][${WORKFLOW_MODE}] detail=${detail}"
  fi
  python3 - "${WORKFLOW_OPS_LOG_PATH}" "${LATEST_WORKFLOW_OPS_PATH}" "${event}" "${stage}" "${status}" "${command}" "${detail}" "${artifacts_csv}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    ops_path,
    latest_path,
    event,
    stage,
    status,
    command,
    detail,
    artifacts_csv,
) = sys.argv[1:]

artifacts = [item for item in artifacts_csv.split("||") if item]
payload = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "event": event,
    "stage": stage,
    "status": status,
    "command": command,
    "detail": detail,
    "artifacts": artifacts,
}
ops_file = Path(ops_path)
ops_file.parent.mkdir(parents=True, exist_ok=True)
with ops_file.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

latest_payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "ops_log_path": str(ops_file.resolve()),
    "last_event": payload,
}
Path(latest_path).write_text(
    json.dumps(latest_payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
}

next_stage_for() {
  case "${1:-}" in
    generate) echo "standalone" ;;
    standalone) echo "acceptance" ;;
    acceptance) echo "done" ;;
    *) echo "generate" ;;
  esac
}

render_cmd() {
  local out=""
  local arg
  for arg in "$@"; do
    out+="$(printf '%q' "${arg}") "
  done
  echo "${out% }"
}

build_dev_resume_command() {
  render_cmd \
    bash "${ROOT_DIR}/scripts/go8_subproject_full_cycle.sh" "${SUBPROJECT_KEY}" \
    --requirements "${REQUIREMENTS}" \
    --module-hints "${MODULE_HINTS}" \
    --max-modules "${MAX_MODULES}" \
    --strategy "${STRATEGY}" \
    --requested-by "${REQUESTED_BY}" \
    --execute "${EXECUTE}" \
    --force-clean "false" \
    --stamp "${STAMP}" \
    --workflow-mode "dev" \
    --state-path "${WORKFLOW_STATE_PATH}" \
    --ops-log-path "${WORKFLOW_OPS_LOG_PATH}" \
    --reset-dev-state "false"
}

build_dev_restart_command() {
  render_cmd \
    bash "${ROOT_DIR}/scripts/go8_subproject_full_cycle.sh" "${SUBPROJECT_KEY}" \
    --requirements "${REQUIREMENTS}" \
    --module-hints "${MODULE_HINTS}" \
    --max-modules "${MAX_MODULES}" \
    --strategy "${STRATEGY}" \
    --requested-by "${REQUESTED_BY}" \
    --execute "${EXECUTE}" \
    --force-clean "${FORCE_CLEAN}" \
    --stamp "${STAMP}" \
    --workflow-mode "dev" \
    --state-path "${WORKFLOW_STATE_PATH}" \
    --ops-log-path "${WORKFLOW_OPS_LOG_PATH}" \
    --reset-dev-state "true"
}

read_current_stage() {
  python3 - "${WORKFLOW_STATE_PATH}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
default = "generate"
if not path.exists():
    print(default)
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print(default)
    raise SystemExit(0)

current = str(payload.get("current_stage") or "").strip().lower()
if current not in {"generate", "standalone", "acceptance", "done"}:
    current = default
print(current)
PY
}

write_workflow_state() {
  local current_stage last_stage last_status next_stage complete
  current_stage="$1"
  last_stage="$2"
  last_status="$3"
  next_stage="$4"
  complete="$5"
  python3 - "${WORKFLOW_STATE_PATH}" "${LATEST_WORKFLOW_STATE_PATH}" "${SUBPROJECT_KEY}" "${STAMP}" "${WORKFLOW_MODE}" "${current_stage}" "${last_stage}" "${last_status}" "${next_stage}" "${complete}" "${WORKFLOW_OPS_LOG_PATH}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    state_path,
    latest_state_path,
    subproject_key,
    stamp,
    workflow_mode,
    current_stage,
    last_stage,
    last_status,
    next_stage,
    complete_raw,
    ops_log_path,
) = sys.argv[1:]

complete = complete_raw.lower() == "true"
payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "subproject_key": subproject_key,
    "stamp": stamp,
    "workflow_mode": workflow_mode,
    "current_stage": current_stage,
    "last_stage": last_stage,
    "last_status": last_status,
    "next_stage": next_stage,
    "complete": complete,
    "ops_log_path": str(Path(ops_log_path).resolve()),
}

for target in (Path(state_path), Path(latest_state_path)):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

AUTO_FINAL_STATUS=""
AUTO_RUN_ID=""
AUTO_REPORT_PATH=""

load_latest_autoevolve() {
  if [[ ! -f "${LATEST_AUTO_PATH}" ]]; then
    return 1
  fi
  local parse_output
  parse_output="$({
    python3 - "${LATEST_AUTO_PATH}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(payload.get("final_status") or "").strip())
print(str(payload.get("run_id") or "").strip())
print(str(payload.get("report_path") or "").strip())
PY
  })"
  AUTO_FINAL_STATUS="$(echo "${parse_output}" | sed -n '1p')"
  AUTO_RUN_ID="$(echo "${parse_output}" | sed -n '2p')"
  AUTO_REPORT_PATH="$(echo "${parse_output}" | sed -n '3p')"
  return 0
}

missing_code_files=()
code_ready="false"
code_file_count="0"
missing_code_csv=""

collect_code_stats() {
  missing_code_files=()
  for file_path in "${REQUIRED_CODE_FILES[@]}"; do
    if [[ ! -f "${file_path}" ]]; then
      missing_code_files+=("${file_path}")
    fi
  done
  if [[ "${#missing_code_files[@]}" -gt 0 ]]; then
    code_ready="false"
  else
    code_ready="true"
  fi
  code_file_count="$(find "${SUBPROJECT_DIR}/backend" "${SUBPROJECT_DIR}/frontend" -type f 2>/dev/null | wc -l | tr -d ' ' || true)"
  if [[ -z "${code_file_count}" ]]; then
    code_file_count="0"
  fi
  missing_code_csv=""
  if [[ "${#missing_code_files[@]}" -gt 0 ]]; then
    missing_code_csv="$(printf '%s||' "${missing_code_files[@]}")"
    missing_code_csv="${missing_code_csv%||}"
  fi
}

write_summary_report() {
  local status run_id auto_report_path code_ready code_file_count missing_code_csv stage_executed next_stage workflow_complete workflow_mode ops_log_path state_path next_command
  status="$1"
  run_id="$2"
  auto_report_path="$3"
  code_ready="$4"
  code_file_count="$5"
  missing_code_csv="$6"
  stage_executed="$7"
  next_stage="$8"
  workflow_complete="$9"
  workflow_mode="${10}"
  ops_log_path="${11}"
  state_path="${12}"
  next_command="${13}"

  mkdir -p "${REPORT_DIR}"
  python3 - "${FULL_CYCLE_REPORT_PATH}" "${LATEST_FULL_CYCLE_PATH}" "${SUBPROJECT_KEY}" "${STAMP}" "${status}" "${run_id}" "${auto_report_path}" "${REQUIREMENTS}" "${code_ready}" "${code_file_count}" "${missing_code_csv}" "${stage_executed}" "${next_stage}" "${workflow_complete}" "${workflow_mode}" "${ops_log_path}" "${state_path}" "${next_command}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    report_path,
    latest_path,
    subproject_key,
    stamp,
    final_status,
    run_id,
    auto_report_path,
    requirements,
    code_ready,
    code_file_count,
    missing_code_csv,
    stage_executed,
    next_stage,
    workflow_complete,
    workflow_mode,
    ops_log_path,
    state_path,
    next_command,
) = sys.argv[1:]

missing_code_files = [item for item in missing_code_csv.split("||") if item]

report_payload = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "mode": "local_rule_engine",
    "model_dependency": False,
    "subproject_key": subproject_key,
    "stamp": stamp,
    "requirements": requirements,
    "final_status": final_status,
    "workflow_run_id": run_id,
    "autoevolve_report_path": auto_report_path,
    "code_ready": code_ready.lower() == "true",
    "code_file_count": int(code_file_count),
    "missing_code_files": missing_code_files,
    "workflow_mode": workflow_mode,
    "workflow_progress": {
        "stage_executed": stage_executed,
        "next_stage": next_stage,
        "complete": workflow_complete.lower() == "true",
        "next_command": next_command,
        "ops_log_path": str(Path(ops_log_path).resolve()),
        "state_path": str(Path(state_path).resolve()),
    },
}
Path(report_path).write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest_payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "report_path": str(Path(report_path).resolve()),
    **report_payload,
}
Path(latest_path).write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

gen_args=(
  "${SUBPROJECT_KEY}"
  --requirements "${REQUIREMENTS}"
  --module-hints "${MODULE_HINTS}"
  --max-modules "${MAX_MODULES}"
  --strategy "${STRATEGY}"
  --requested-by "${REQUESTED_BY}"
  --execute "${EXECUTE}"
)
if is_true "${FORCE_CLEAN}"; then
  gen_args+=(--force-clean)
fi

run_stage_generate() {
  local cmd_desc
  cmd_desc="bash ${ROOT_DIR}/scripts/stationctl.sh subproject-generate ${SUBPROJECT_KEY} --requirements <normalized> --module-hints ${MODULE_HINTS} --max-modules ${MAX_MODULES} --strategy ${STRATEGY} --requested-by ${REQUESTED_BY} --execute ${EXECUTE}"
  log_op "command" "generate" "start" "${cmd_desc}" "" ""
  if bash "${ROOT_DIR}/scripts/stationctl.sh" subproject-generate "${gen_args[@]}"; then
    log_op "command" "generate" "success" "${cmd_desc}" "" "${SUBPROJECT_DIR}/README.md||${CONFIG_PATH}||${SUBPROJECT_DIR}/scripts/run.sh"
  else
    local rc="$?"
    log_op "command" "generate" "failed" "${cmd_desc}" "exit_code=${rc}" ""
    exit "${rc}"
  fi
}

run_stage_standalone() {
  local cmd_desc
  cmd_desc="bash ${SUBPROJECT_DIR}/scripts/run.sh ${STAMP}"
  log_op "command" "standalone" "start" "${cmd_desc}" "" ""
  if bash "${SUBPROJECT_DIR}/scripts/run.sh" "${STAMP}"; then
    log_op "command" "standalone" "success" "${cmd_desc}" "" "${LATEST_AUTO_PATH}"
  else
    local rc="$?"
    log_op "command" "standalone" "failed" "${cmd_desc}" "exit_code=${rc}" ""
    exit "${rc}"
  fi
}

run_stage_acceptance() {
  if ! load_latest_autoevolve; then
    log_op "check" "acceptance" "failed" "load latest autoevolve summary" "missing ${LATEST_AUTO_PATH}" "${LATEST_AUTO_PATH}"
    echo "missing ${LATEST_AUTO_PATH}"
    exit 1
  fi
}

if [[ "${WORKFLOW_MODE}" == "dev" ]] && is_true "${RESET_DEV_STATE}"; then
  rm -f "${WORKFLOW_STATE_PATH}" "${LATEST_WORKFLOW_STATE_PATH}"
  log_op "state" "dev" "reset" "reset dev workflow state" "" "${WORKFLOW_STATE_PATH}||${LATEST_WORKFLOW_STATE_PATH}"
fi

stage_executed=""
next_stage="generate"
workflow_complete="false"

stages=()
if [[ "${WORKFLOW_MODE}" == "dev" ]]; then
  current_stage="$(read_current_stage)"
  if [[ "${current_stage}" == "done" ]]; then
    workflow_complete="true"
    stage_executed="none"
    next_stage="done"
    log_op "state" "dev" "info" "workflow already complete" "" "${WORKFLOW_STATE_PATH}"
  else
    stages=("${current_stage}")
  fi
else
  stages=("generate" "standalone" "acceptance")
fi

for stage in "${stages[@]}"; do
  case "${stage}" in
    generate)
      echo "[go8 1/3] generate requirement-driven subproject"
      run_stage_generate
      ;;
    standalone)
      echo "[go8 2/3] run standalone local flow"
      run_stage_standalone
      ;;
    acceptance)
      echo "[go8 3/3] write acceptance report"
      run_stage_acceptance
      ;;
    *)
      echo "unknown stage: ${stage}"
      exit 1
      ;;
  esac

  stage_executed="${stage}"
  next_stage="$(next_stage_for "${stage}")"
  if [[ "${next_stage}" == "done" ]]; then
    workflow_complete="true"
  fi
  if [[ "${WORKFLOW_MODE}" == "dev" ]]; then
    write_workflow_state "${next_stage}" "${stage}" "success" "${next_stage}" "${workflow_complete}"
  fi
done

if [[ "${WORKFLOW_MODE}" == "test" ]]; then
  stage_executed="acceptance"
  next_stage="done"
  workflow_complete="true"
  write_workflow_state "done" "acceptance" "success" "done" "true"
fi

AUTO_FINAL_STATUS=""
AUTO_RUN_ID=""
AUTO_REPORT_PATH=""
if [[ -f "${LATEST_AUTO_PATH}" ]]; then
  load_latest_autoevolve || true
fi

collect_code_stats

final_status="in_progress"
if [[ "${WORKFLOW_MODE}" == "test" || "${workflow_complete}" == "true" ]]; then
  if [[ -z "${AUTO_FINAL_STATUS}" ]]; then
    final_status="failed"
  else
    final_status="${AUTO_FINAL_STATUS}"
  fi
fi

workflow_next_command=""
if [[ "${WORKFLOW_MODE}" == "dev" ]]; then
  if [[ "${workflow_complete}" == "true" ]]; then
    workflow_next_command="$(build_dev_restart_command)"
  else
    workflow_next_command="$(build_dev_resume_command)"
  fi
  log_op "hint" "dev" "next_command" "next step command" "${workflow_next_command}" ""
fi

write_summary_report "${final_status}" "${AUTO_RUN_ID}" "${AUTO_REPORT_PATH}" "${code_ready}" "${code_file_count}" "${missing_code_csv}" "${stage_executed:-none}" "${next_stage}" "${workflow_complete}" "${WORKFLOW_MODE}" "${WORKFLOW_OPS_LOG_PATH}" "${WORKFLOW_STATE_PATH}" "${workflow_next_command}"
log_op "file_write" "report" "success" "write full-cycle summary report" "" "${FULL_CYCLE_REPORT_PATH}||${LATEST_FULL_CYCLE_PATH}"

echo "full_cycle_report=${FULL_CYCLE_REPORT_PATH}"
echo "latest_full_cycle=${LATEST_FULL_CYCLE_PATH}"
echo "mode=local_rule_engine"
echo "model_dependency=false"
echo "workflow_mode=${WORKFLOW_MODE}"
echo "workflow_stage_executed=${stage_executed:-none}"
echo "workflow_next_stage=${next_stage}"
echo "workflow_complete=${workflow_complete}"
echo "workflow_state_path=${WORKFLOW_STATE_PATH}"
echo "workflow_ops_log_path=${WORKFLOW_OPS_LOG_PATH}"
if [[ -n "${workflow_next_command}" ]]; then
  echo "workflow_next_command=${workflow_next_command}"
fi
echo "final_status=${final_status}"
echo "workflow_run_id=${AUTO_RUN_ID}"
echo "code_ready=${code_ready}"
echo "code_file_count=${code_file_count}"

if [[ "${WORKFLOW_MODE}" == "test" || "${workflow_complete}" == "true" ]]; then
  if [[ "${final_status}" != "succeeded" ]]; then
    exit 4
  fi
  if [[ "${code_ready}" != "true" ]]; then
    echo "missing_code_files=${missing_code_csv}"
    exit 5
  fi
fi
