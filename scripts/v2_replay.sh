#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBPROJECT_KEY="stock-sentiment"
SUBPROJECT_KEY_SET="false"
MODE="build"
SNAPSHOT_FILE=""
LATEST_V2_REPORT=""
SOURCE_REPORT=""
USE_LATEST_PARAMS="true"
REQUESTED_BY="v2-replay"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${ROOT_DIR}/docs/v2_reports"
LATEST_REPORT_PATH=""
MODULE_HINTS=""
MAX_MODULES=""
STRATEGY=""
EXECUTE=""
FORCE_CLEAN=""
WORKFLOW_MODE=""
DRY_RUN="false"

usage() {
  cat <<'EOF_USAGE'
Usage:
  bash scripts/v2_replay.sh [subproject_key] [options]

Options:
  --mode <plan|build>             default: build
  --snapshot-file <path>          default: project/<subproject>/REQUIREMENTS.md
  --source-report <path>          replay from selected report payload (or latest pointer file)
  --latest-v2-report <path>       default: docs/v2_reports/latest_<subproject>_v2_run.json
  --use-latest-params <true|false> default: true
  --module-hints <csv>            override module hints
  --max-modules <n>               override max modules
  --strategy <speed|balanced|safe> override strategy
  --execute <true|false>          override execute
  --force-clean <true|false>      override force clean
  --workflow-mode <test|dev>      override workflow mode
  --requested-by <name>           default: v2-replay
  --stamp <utc_stamp>             default: now
  --report-dir <path>             default: docs/v2_reports
  --latest-report <path>          default: docs/v2_reports/latest_<subproject>_v2_run.json
  --dry-run                       print effective v2_run command only
  -h, --help
EOF_USAGE
}

if [[ $# -gt 0 && ( "${1:-}" == "-h" || "${1:-}" == "--help" || "${1:-}" == "help" ) ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 && "${1:-}" != -* ]]; then
  SUBPROJECT_KEY="${1:-}"
  SUBPROJECT_KEY_SET="true"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift
      ;;
    --snapshot-file)
      SNAPSHOT_FILE="${2:-}"
      shift
      ;;
    --source-report)
      SOURCE_REPORT="${2:-}"
      shift
      ;;
    --latest-v2-report)
      LATEST_V2_REPORT="${2:-}"
      shift
      ;;
    --use-latest-params)
      USE_LATEST_PARAMS="${2:-}"
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
    --dry-run)
      DRY_RUN="true"
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

normalize_bool() {
  echo "$1" | tr '[:upper:]' '[:lower:]'
}

if [[ -n "${SOURCE_REPORT}" ]]; then
  if [[ ! -f "${SOURCE_REPORT}" ]]; then
    echo "source report not found: ${SOURCE_REPORT}"
    exit 1
  fi
  source_parsed="$({
    python3 - "${SOURCE_REPORT}" "${ROOT_DIR}" <<'PY'
import json
import sys
from pathlib import Path

source_path = Path(sys.argv[1]).resolve()
root_dir = Path(sys.argv[2]).resolve()
payload = json.loads(source_path.read_text(encoding="utf-8"))
report_path = str(payload.get("report_path") or "").strip()
if report_path:
    candidate = Path(report_path)
    if not candidate.is_absolute():
        candidate = (source_path.parent / candidate).resolve()
    if candidate.exists():
        payload = json.loads(candidate.read_text(encoding="utf-8"))

run_section = payload.get("run") or {}
input_section = payload.get("input") or {}
requirement_file = str(input_section.get("requirement_file") or "").strip()
if requirement_file:
    req_path = Path(requirement_file)
    if not req_path.is_absolute():
        req_path = (root_dir / req_path).resolve()
    requirement_file = str(req_path)

print(str(run_section.get("subproject_key") or "").strip())
print(requirement_file)
print(str(input_section.get("module_hints") or "").strip())
print(str(input_section.get("max_modules") or "").strip())
print(str(input_section.get("strategy") or "").strip())
execute = input_section.get("execute")
if isinstance(execute, bool):
    print("true" if execute else "false")
else:
    print(str(execute or "").strip().lower())
force_clean = input_section.get("force_clean")
if isinstance(force_clean, bool):
    print("true" if force_clean else "false")
else:
    print(str(force_clean or "").strip().lower())
print(str(input_section.get("workflow_mode") or "").strip())
PY
  })"
  source_subproject="$(echo "${source_parsed}" | sed -n '1p')"
  source_requirement_file="$(echo "${source_parsed}" | sed -n '2p')"
  source_module_hints="$(echo "${source_parsed}" | sed -n '3p')"
  source_max_modules="$(echo "${source_parsed}" | sed -n '4p')"
  source_strategy="$(echo "${source_parsed}" | sed -n '5p')"
  source_execute="$(echo "${source_parsed}" | sed -n '6p')"
  source_force_clean="$(echo "${source_parsed}" | sed -n '7p')"
  source_workflow_mode="$(echo "${source_parsed}" | sed -n '8p')"

  if [[ "${SUBPROJECT_KEY_SET}" != "true" && -n "${source_subproject}" ]]; then
    SUBPROJECT_KEY="${source_subproject}"
  fi
  if [[ -z "${SNAPSHOT_FILE}" && -n "${source_requirement_file}" ]]; then
    SNAPSHOT_FILE="${source_requirement_file}"
  fi
  if [[ -z "${MODULE_HINTS}" && -n "${source_module_hints}" ]]; then
    MODULE_HINTS="${source_module_hints}"
  fi
  if [[ -z "${MAX_MODULES}" && -n "${source_max_modules}" ]]; then
    MAX_MODULES="${source_max_modules}"
  fi
  if [[ -z "${STRATEGY}" && -n "${source_strategy}" ]]; then
    STRATEGY="${source_strategy}"
  fi
  if [[ -z "${EXECUTE}" && -n "${source_execute}" ]]; then
    EXECUTE="${source_execute}"
  fi
  if [[ -z "${FORCE_CLEAN}" && -n "${source_force_clean}" ]]; then
    FORCE_CLEAN="${source_force_clean}"
  fi
  if [[ -z "${WORKFLOW_MODE}" && -n "${source_workflow_mode}" ]]; then
    WORKFLOW_MODE="${source_workflow_mode}"
  fi
fi

if [[ -z "${SNAPSHOT_FILE}" ]]; then
  SNAPSHOT_FILE="${ROOT_DIR}/project/${SUBPROJECT_KEY}/REQUIREMENTS.md"
fi
if [[ ! -f "${SNAPSHOT_FILE}" ]]; then
  echo "snapshot requirement file not found: ${SNAPSHOT_FILE}"
  exit 1
fi

if [[ -z "${LATEST_V2_REPORT}" ]]; then
  LATEST_V2_REPORT="${ROOT_DIR}/docs/v2_reports/latest_${SUBPROJECT_KEY}_v2_run.json"
fi

if [[ "$(normalize_bool "${USE_LATEST_PARAMS}")" == "true" && -f "${LATEST_V2_REPORT}" ]]; then
  parsed="$({
    python3 - "${LATEST_V2_REPORT}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
input_section = payload.get("input") or {}
print(str(input_section.get("module_hints") or "").strip())
print(str(input_section.get("max_modules") or "").strip())
print(str(input_section.get("strategy") or "").strip())
execute = input_section.get("execute")
if isinstance(execute, bool):
    print("true" if execute else "false")
else:
    print(str(execute or "").strip().lower())
force_clean = input_section.get("force_clean")
if isinstance(force_clean, bool):
    print("true" if force_clean else "false")
else:
    print(str(force_clean or "").strip().lower())
print(str(input_section.get("workflow_mode") or "").strip())
PY
  })"
  latest_module_hints="$(echo "${parsed}" | sed -n '1p')"
  latest_max_modules="$(echo "${parsed}" | sed -n '2p')"
  latest_strategy="$(echo "${parsed}" | sed -n '3p')"
  latest_execute="$(echo "${parsed}" | sed -n '4p')"
  latest_force_clean="$(echo "${parsed}" | sed -n '5p')"
  latest_workflow_mode="$(echo "${parsed}" | sed -n '6p')"

  if [[ -z "${MODULE_HINTS}" ]]; then
    MODULE_HINTS="${latest_module_hints}"
  fi
  if [[ -z "${MAX_MODULES}" ]]; then
    MAX_MODULES="${latest_max_modules}"
  fi
  if [[ -z "${STRATEGY}" ]]; then
    STRATEGY="${latest_strategy}"
  fi
  if [[ -z "${EXECUTE}" ]]; then
    EXECUTE="${latest_execute}"
  fi
  if [[ -z "${FORCE_CLEAN}" ]]; then
    FORCE_CLEAN="${latest_force_clean}"
  fi
  if [[ -z "${WORKFLOW_MODE}" ]]; then
    WORKFLOW_MODE="${latest_workflow_mode}"
  fi
fi

cmd=(bash "${ROOT_DIR}/scripts/v2_run.sh" "${SUBPROJECT_KEY}")
cmd+=(--mode "${MODE}")
cmd+=(--requirement-file "${SNAPSHOT_FILE}")
cmd+=(--requested-by "${REQUESTED_BY}")
cmd+=(--stamp "${STAMP}")
cmd+=(--report-dir "${REPORT_DIR}")

if [[ -n "${LATEST_REPORT_PATH}" ]]; then
  cmd+=(--latest-report "${LATEST_REPORT_PATH}")
fi
if [[ -n "${MODULE_HINTS}" ]]; then
  cmd+=(--module-hints "${MODULE_HINTS}")
fi
if [[ -n "${MAX_MODULES}" ]]; then
  cmd+=(--max-modules "${MAX_MODULES}")
fi
if [[ -n "${STRATEGY}" ]]; then
  cmd+=(--strategy "${STRATEGY}")
fi
if [[ -n "${EXECUTE}" ]]; then
  cmd+=(--execute "${EXECUTE}")
fi
if [[ -n "${FORCE_CLEAN}" ]]; then
  cmd+=(--force-clean "${FORCE_CLEAN}")
fi
if [[ -n "${WORKFLOW_MODE}" ]]; then
  cmd+=(--workflow-mode "${WORKFLOW_MODE}")
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  printf '[dry-run]'
  for arg in "${cmd[@]}"; do
    printf ' %q' "${arg}"
  done
  printf '\n'
  exit 0
fi

"${cmd[@]}"
