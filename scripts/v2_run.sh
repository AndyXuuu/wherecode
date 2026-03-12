#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBPROJECT_KEY="${1:-stock-sentiment}"
MODE="build"
REQUIREMENT_FILE=""
MODULE_HINTS="crawl,sentiment,entity-linking,industry,theme,risk,report"
MAX_MODULES="7"
STRATEGY="balanced"
EXECUTE="true"
FORCE_CLEAN="true"
REQUESTED_BY="v2-run"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${ROOT_DIR}/docs/v2_reports"
LATEST_REPORT_PATH=""
WORKFLOW_MODE="test"
WORKFLOW_STATE_PATH=""
WORKFLOW_OPS_LOG_PATH=""
RESET_DEV_STATE="false"

usage() {
  cat <<'EOF_USAGE'
Usage:
  bash scripts/v2_run.sh [subproject_key] [options]

Options:
  --mode <plan|build>              default: build
  --requirement-file <path>        default: project/<subproject>/REQUIREMENTS.md
  --module-hints <csv>             default: crawl,sentiment,entity-linking,industry,theme,risk,report
  --max-modules <n>                default: 7
  --strategy <speed|balanced|safe> default: balanced
  --execute <true|false>           default: true
  --force-clean <true|false>       default: true
  --workflow-mode <test|dev>       default: test
  --state-path <path>              forwarded to go8 (dev cursor file)
  --ops-log-path <path>            forwarded to go8 (operation log file)
  --reset-dev-state <true|false>   forwarded to go8, default: false
  --requested-by <name>            default: v2-run
  --stamp <utc_stamp>              default: now
  --report-dir <path>              default: docs/v2_reports
  --latest-report <path>           default: docs/v2_reports/latest_<subproject>_v2_run.json
  -h, --help
EOF_USAGE
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
    --mode)
      MODE="${2:-}"
      shift
      ;;
    --requirement-file)
      REQUIREMENT_FILE="${2:-}"
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
    --force-clean)
      FORCE_CLEAN="${2:-}"
      shift
      ;;
    --workflow-mode)
      WORKFLOW_MODE="${2:-}"
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
    --requested-by)
      REQUESTED_BY="${2:-}"
      shift
      ;;
    --stamp)
      STAMP="${2:-}"
      shift
      ;;
    --report-dir)
      REPORT_DIR="${2:-}"
      shift
      ;;
    --latest-report)
      LATEST_REPORT_PATH="${2:-}"
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

MODE="$(echo "${MODE}" | tr '[:upper:]' '[:lower:]')"
if [[ "${MODE}" != "plan" && "${MODE}" != "build" ]]; then
  echo "mode must be plan|build"
  exit 1
fi

WORKFLOW_MODE="$(echo "${WORKFLOW_MODE}" | tr '[:upper:]' '[:lower:]')"
if [[ "${WORKFLOW_MODE}" != "test" && "${WORKFLOW_MODE}" != "dev" ]]; then
  echo "workflow-mode must be test|dev"
  exit 1
fi

if [[ -z "${REQUIREMENT_FILE}" ]]; then
  canonical_requirement_file="${ROOT_DIR}/project/requirements/${SUBPROJECT_KEY}.md"
  legacy_requirement_file="${ROOT_DIR}/project/${SUBPROJECT_KEY}/REQUIREMENTS.md"
  if [[ -f "${canonical_requirement_file}" ]]; then
    REQUIREMENT_FILE="${canonical_requirement_file}"
  else
    REQUIREMENT_FILE="${legacy_requirement_file}"
  fi
fi

if [[ ! -f "${REQUIREMENT_FILE}" ]]; then
  echo "requirement file not found: ${REQUIREMENT_FILE}"
  exit 1
fi

REQUIREMENTS="$({
  python3 - "${REQUIREMENT_FILE}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
lines = []
for raw in text.splitlines():
    line = raw.strip()
    if not line:
        continue
    if line.startswith("#"):
        continue
    lines.append(line)
print(" ".join(lines).strip())
PY
})"

if [[ -z "${REQUIREMENTS}" ]]; then
  echo "empty requirements after normalization: ${REQUIREMENT_FILE}"
  exit 1
fi

mkdir -p "${REPORT_DIR}"
REPORT_PATH="${REPORT_DIR}/${STAMP}-${SUBPROJECT_KEY}-v2-run.json"
if [[ -z "${LATEST_REPORT_PATH}" ]]; then
  LATEST_REPORT_PATH="${REPORT_DIR}/latest_${SUBPROJECT_KEY}_v2_run.json"
fi

PLAN_OUTPUT=""
BUILD_OUTPUT=""
FULL_CYCLE_REPORT_PATH=""
FULL_CYCLE_STATUS=""
FULL_CYCLE_WORKFLOW_RUN_ID=""
FULL_CYCLE_WORKFLOW_MODE=""
FULL_CYCLE_WORKFLOW_STAGE_EXECUTED=""
FULL_CYCLE_WORKFLOW_NEXT_STAGE=""
FULL_CYCLE_WORKFLOW_COMPLETE="false"
FULL_CYCLE_WORKFLOW_NEXT_COMMAND=""
FULL_CYCLE_WORKFLOW_OPS_LOG_PATH=""
FULL_CYCLE_WORKFLOW_STATE_PATH=""
FINAL_STATUS="success"

if [[ "${MODE}" == "plan" ]]; then
  PLAN_OUTPUT="$(bash "${ROOT_DIR}/scripts/stationctl.sh" --dry-run main-orchestrate --requirements "${REQUIREMENTS}" --execute false 2>&1)"
else
  go8_cmd=(
    bash "${ROOT_DIR}/scripts/go8_subproject_full_cycle.sh" "${SUBPROJECT_KEY}"
    --requirements "${REQUIREMENTS}"
    --module-hints "${MODULE_HINTS}"
    --max-modules "${MAX_MODULES}"
    --strategy "${STRATEGY}"
    --requested-by "${REQUESTED_BY}"
    --execute "${EXECUTE}"
    --force-clean "${FORCE_CLEAN}"
    --stamp "${STAMP}"
    --workflow-mode "${WORKFLOW_MODE}"
    --reset-dev-state "${RESET_DEV_STATE}"
  )
  if [[ -n "${WORKFLOW_STATE_PATH}" ]]; then
    go8_cmd+=(--state-path "${WORKFLOW_STATE_PATH}")
  fi
  if [[ -n "${WORKFLOW_OPS_LOG_PATH}" ]]; then
    go8_cmd+=(--ops-log-path "${WORKFLOW_OPS_LOG_PATH}")
  fi

  BUILD_OUTPUT="$("${go8_cmd[@]}" 2>&1)"

  latest_full_cycle="${ROOT_DIR}/project/${SUBPROJECT_KEY}/reports/latest_full_cycle.json"
  if [[ -f "${latest_full_cycle}" ]]; then
    parsed="$({
      python3 - "${latest_full_cycle}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(payload.get("report_path") or "").strip())
print(str(payload.get("final_status") or "").strip())
print(str(payload.get("workflow_run_id") or "").strip())
print(str(payload.get("workflow_mode") or "").strip())
progress = payload.get("workflow_progress") if isinstance(payload, dict) else {}
if not isinstance(progress, dict):
    progress = {}
print(str(progress.get("stage_executed") or "").strip())
print(str(progress.get("next_stage") or "").strip())
print("true" if bool(progress.get("complete")) else "false")
print(str(progress.get("next_command") or "").strip())
print(str(progress.get("ops_log_path") or "").strip())
print(str(progress.get("state_path") or "").strip())
PY
    })"
    FULL_CYCLE_REPORT_PATH="$(echo "${parsed}" | sed -n '1p')"
    FULL_CYCLE_STATUS="$(echo "${parsed}" | sed -n '2p')"
    FULL_CYCLE_WORKFLOW_RUN_ID="$(echo "${parsed}" | sed -n '3p')"
    FULL_CYCLE_WORKFLOW_MODE="$(echo "${parsed}" | sed -n '4p')"
    FULL_CYCLE_WORKFLOW_STAGE_EXECUTED="$(echo "${parsed}" | sed -n '5p')"
    FULL_CYCLE_WORKFLOW_NEXT_STAGE="$(echo "${parsed}" | sed -n '6p')"
    FULL_CYCLE_WORKFLOW_COMPLETE="$(echo "${parsed}" | sed -n '7p')"
    FULL_CYCLE_WORKFLOW_NEXT_COMMAND="$(echo "${parsed}" | sed -n '8p')"
    FULL_CYCLE_WORKFLOW_OPS_LOG_PATH="$(echo "${parsed}" | sed -n '9p')"
    FULL_CYCLE_WORKFLOW_STATE_PATH="$(echo "${parsed}" | sed -n '10p')"
  fi

  normalized_full_cycle_status="$(echo "${FULL_CYCLE_STATUS}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${WORKFLOW_MODE}" == "dev" ]]; then
    if [[ "${normalized_full_cycle_status}" != "success" && "${normalized_full_cycle_status}" != "succeeded" && "${normalized_full_cycle_status}" != "in_progress" ]]; then
      FINAL_STATUS="failed"
    fi
  else
    if [[ "${normalized_full_cycle_status}" != "success" && "${normalized_full_cycle_status}" != "succeeded" ]]; then
      FINAL_STATUS="failed"
    fi
  fi
fi

subproject_requirement_snapshot="${ROOT_DIR}/project/${SUBPROJECT_KEY}/REQUIREMENTS.md"
mkdir -p "$(dirname "${subproject_requirement_snapshot}")"
python3 - "${subproject_requirement_snapshot}" "${REQUIREMENTS}" <<'PY'
from pathlib import Path
import sys

target = Path(sys.argv[1])
requirements = sys.argv[2].strip()
target.write_text("# Requirement Snapshot\n\n" + requirements + "\n", encoding="utf-8")
PY

python3 - "${REPORT_PATH}" "${LATEST_REPORT_PATH}" "${STAMP}" "${SUBPROJECT_KEY}" "${MODE}" "${WORKFLOW_MODE}" "${REQUIREMENT_FILE}" "${REQUIREMENTS}" "${MODULE_HINTS}" "${MAX_MODULES}" "${STRATEGY}" "${EXECUTE}" "${FORCE_CLEAN}" "${FINAL_STATUS}" "${FULL_CYCLE_STATUS}" "${FULL_CYCLE_WORKFLOW_RUN_ID}" "${FULL_CYCLE_REPORT_PATH}" "${FULL_CYCLE_WORKFLOW_STAGE_EXECUTED}" "${FULL_CYCLE_WORKFLOW_NEXT_STAGE}" "${FULL_CYCLE_WORKFLOW_COMPLETE}" "${FULL_CYCLE_WORKFLOW_NEXT_COMMAND}" "${FULL_CYCLE_WORKFLOW_OPS_LOG_PATH}" "${FULL_CYCLE_WORKFLOW_STATE_PATH}" "${REQUESTED_BY}" "${PLAN_OUTPUT}" "${BUILD_OUTPUT}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    report_path,
    latest_path,
    stamp,
    subproject_key,
    mode,
    workflow_mode,
    requirement_file,
    requirements,
    module_hints,
    max_modules,
    strategy,
    execute,
    force_clean,
    final_status,
    full_cycle_status,
    workflow_run_id,
    full_cycle_report_path,
    workflow_stage_executed,
    workflow_next_stage,
    workflow_complete,
    workflow_next_command,
    workflow_ops_log_path,
    workflow_state_path,
    requested_by,
    plan_output,
    build_output,
) = sys.argv[1:]


def _norm(value: str) -> str:
    return str(value or "").strip().lower()


def _contains_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


mode_norm = _norm(mode)
final_status_norm = _norm(final_status)
full_cycle_status_norm = _norm(full_cycle_status)
plan_output_norm = (plan_output or "").lower()
build_output_norm = (build_output or "").lower()

taxonomy_code = "success"
taxonomy_stage = "none"
taxonomy_severity = "none"
taxonomy_reason = "run completed successfully"

if final_status_norm not in {"success", "succeeded"}:
    taxonomy_stage = mode_norm if mode_norm in {"plan", "build"} else "unknown"
    if mode_norm == "plan":
        if _contains_any(
            plan_output_norm,
            ["clarification", "ambiguous", "tbd", "todo", "???", "待定", "不确定"],
        ):
            taxonomy_code = "clarification_required"
            taxonomy_severity = "medium"
            taxonomy_reason = "requirements are ambiguous and need clarification before orchestration."
        else:
            taxonomy_code = "plan_generation_failed"
            taxonomy_severity = "high"
            taxonomy_reason = "failed to generate orchestration plan from requirements."
    else:
        if "timeout" in build_output_norm:
            taxonomy_code = "execution_timeout"
            taxonomy_severity = "high"
            taxonomy_reason = "subproject execution timed out."
        elif _contains_any(
            build_output_norm,
            [
                "failed to connect",
                "connection refused",
                "service unavailable",
                "temporary failure",
                "curl: (7)",
                "http 502",
                "http 503",
                "http 504",
            ],
        ):
            taxonomy_code = "dependency_unavailable"
            taxonomy_severity = "high"
            taxonomy_reason = "required runtime dependency was not reachable."
        elif _contains_any(
            build_output_norm,
            ["permission denied", "unauthorized", "forbidden"],
        ):
            taxonomy_code = "permission_blocked"
            taxonomy_severity = "high"
            taxonomy_reason = "execution was blocked by permission/auth constraints."
        elif full_cycle_status_norm and full_cycle_status_norm not in {
            "success",
            "succeeded",
        }:
            taxonomy_code = "full_cycle_failed"
            taxonomy_severity = "high"
            taxonomy_reason = "full-cycle report returned non-success status."
        else:
            taxonomy_code = "execution_failed"
            taxonomy_severity = "high"
            taxonomy_reason = "execution failed with an unknown error."

retry_hints_map = {
    "success": [
        "No retry required. Keep this report as baseline for next runs.",
    ],
    "clarification_required": [
        "Clarify requirement text and remove ambiguous markers (tbd/todo/???).",
        "Rerun with updated requirement file, then execute plan/build again.",
    ],
    "plan_generation_failed": [
        "Reduce requirement complexity and module count, then rerun in plan mode.",
        "Check control_center/action_layer availability before rerun.",
    ],
    "execution_timeout": [
        "Retry with smaller module scope or safer strategy.",
        "Check host load and rerun from snapshot via v2-replay.",
    ],
    "dependency_unavailable": [
        "Start required local services and verify endpoint reachability.",
        "Retry after dependency recovery using v2-replay.",
    ],
    "permission_blocked": [
        "Fix token/permission configuration and rerun.",
        "Validate env/auth settings in control_center and action_layer.",
    ],
    "full_cycle_failed": [
        "Inspect subproject latest_full_cycle report and failed stage logs.",
        "Apply recovery action then rerun from requirement snapshot.",
    ],
    "execution_failed": [
        "Inspect build_output logs and full-cycle report for exact failed step.",
        "Retry from snapshot in plan mode first, then build mode.",
    ],
}

next_commands_map = {
    "success": [
        "bash scripts/check_all.sh v2",
        f"bash scripts/stationctl.sh v2-replay {subproject_key} --mode plan",
    ],
    "clarification_required": [
        f"bash scripts/stationctl.sh v2-run {subproject_key} --mode plan",
    ],
    "plan_generation_failed": [
        f"bash scripts/stationctl.sh v2-run {subproject_key} --mode plan",
        "bash scripts/check_all.sh main --local",
    ],
    "execution_timeout": [
        f"bash scripts/stationctl.sh v2-replay {subproject_key} --mode build --strategy safe",
    ],
    "dependency_unavailable": [
        f"bash scripts/stationctl.sh v2-replay {subproject_key} --mode build",
        "bash scripts/stationctl.sh orchestrate-policy",
    ],
    "permission_blocked": [
        f"bash scripts/stationctl.sh v2-replay {subproject_key} --mode plan",
    ],
    "full_cycle_failed": [
        f"bash scripts/stationctl.sh v2-replay {subproject_key} --mode plan",
        f"bash scripts/stationctl.sh v2-replay {subproject_key} --mode build",
    ],
    "execution_failed": [
        f"bash scripts/stationctl.sh v2-replay {subproject_key} --mode plan",
        "bash scripts/check_all.sh v2 --local",
    ],
}

retry_hints = retry_hints_map.get(taxonomy_code, retry_hints_map["execution_failed"])
next_commands = next_commands_map.get(
    taxonomy_code, next_commands_map["execution_failed"]
)

payload = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "version": "v2",
    "benchmark": {
        "targets": ["openclaw", "opencode", "oh-my-opencode"],
        "aligned_capabilities": [
            "single_command_entry",
            "plan_or_build_modes",
            "autonomous_execution_loop",
            "structured_run_artifacts",
            "human_checkpoint_at_milestones",
        ],
    },
    "run": {
        "stamp": stamp,
        "subproject_key": subproject_key,
        "mode": mode,
        "workflow_mode": workflow_mode,
        "requested_by": requested_by,
        "final_status": final_status,
    },
    "input": {
        "requirement_file": requirement_file,
        "requirements": requirements,
        "module_hints": module_hints,
        "max_modules": int(max_modules),
        "strategy": strategy,
        "execute": execute.lower() == "true",
        "force_clean": force_clean.lower() == "true",
        "workflow_mode": workflow_mode,
    },
    "outputs": {
        "full_cycle_status": full_cycle_status,
        "workflow_run_id": workflow_run_id,
        "full_cycle_report_path": full_cycle_report_path,
        "workflow_stage_executed": workflow_stage_executed,
        "workflow_next_stage": workflow_next_stage,
        "workflow_complete": workflow_complete.lower() == "true",
        "workflow_next_command": workflow_next_command,
        "workflow_ops_log_path": workflow_ops_log_path,
        "workflow_state_path": workflow_state_path,
    },
    "diagnosis": {
        "failure_taxonomy": {
            "code": taxonomy_code,
            "stage": taxonomy_stage,
            "severity": taxonomy_severity,
            "reason": taxonomy_reason,
        },
        "retry_hints": retry_hints,
        "next_commands": next_commands,
    },
    "logs": {
        "plan_output": plan_output,
        "build_output": build_output,
    },
}

report = Path(report_path)
report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest = Path(latest_path)
latest.parent.mkdir(parents=True, exist_ok=True)
latest.write_text(
    json.dumps(
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "report_path": str(report.resolve()),
            **payload,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY

echo "v2_report=${REPORT_PATH}"
echo "v2_latest=${LATEST_REPORT_PATH}"
echo "mode=${MODE}"
echo "workflow_mode=${WORKFLOW_MODE}"
echo "subproject=${SUBPROJECT_KEY}"
echo "status=${FINAL_STATUS}"
if [[ "${MODE}" == "build" ]]; then
  echo "workflow_stage_executed=${FULL_CYCLE_WORKFLOW_STAGE_EXECUTED}"
  echo "workflow_next_stage=${FULL_CYCLE_WORKFLOW_NEXT_STAGE}"
  echo "workflow_complete=${FULL_CYCLE_WORKFLOW_COMPLETE}"
  if [[ -n "${FULL_CYCLE_WORKFLOW_NEXT_COMMAND}" ]]; then
    echo "workflow_next_command=${FULL_CYCLE_WORKFLOW_NEXT_COMMAND}"
  fi
  echo "workflow_ops_log_path=${FULL_CYCLE_WORKFLOW_OPS_LOG_PATH}"
  echo "workflow_state_path=${FULL_CYCLE_WORKFLOW_STATE_PATH}"
fi
