#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN_PATH="${ROOT_DIR}/PLAN.md"
CONTROL_URL="${WHERECODE_CONTROL_URL:-http://127.0.0.1:8000}"
REPORT_ROOT="${ROOT_DIR}/docs/ops_reports/plan_autopilot"

REQUESTED_BY="${PLAN_AUTOPILOT_REQUESTED_BY:-plan-autopilot}"
CONFIRMED_BY="${PLAN_AUTOPILOT_CONFIRMED_BY:-owner}"
MODULE_HINTS="${PLAN_AUTOPILOT_MODULE_HINTS:-requirements,implementation,testing,documentation}"
MAX_MODULES="${PLAN_AUTOPILOT_MAX_MODULES:-6}"
STRATEGY="${PLAN_AUTOPILOT_STRATEGY:-balanced}"
EXECUTE="${PLAN_AUTOPILOT_EXECUTE:-true}"
FORCE_REDECOMPOSE="${PLAN_AUTOPILOT_FORCE_REDECOMPOSE:-false}"
REQUIRE_FINAL_NEXT_ACTION="${PLAN_AUTOPILOT_REQUIRE_FINAL_NEXT_ACTION:-true}"
VERIFY_CMD="${PLAN_AUTOPILOT_VERIFY_CMD:-}"

MAX_TASKS="${PLAN_AUTOPILOT_MAX_TASKS:-0}"
MAX_RETRIES="${PLAN_AUTOPILOT_MAX_RETRIES:-0}"
RETRY_INTERVAL_SECONDS="${PLAN_AUTOPILOT_RETRY_INTERVAL_SECONDS:-5}"
DRY_RUN=false
STRICT_MODE=true
TASK_FAIL_REASON=""

usage() {
  cat <<'EOF'
Usage:
  bash scripts/plan_autopilot.sh [options]

Options:
  --plan <path>                    default: PLAN.md in repo root
  --control-url <url>              default: http://127.0.0.1:8000
  --report-root <path>             default: docs/ops_reports/plan_autopilot
  --requested-by <name>            default: plan-autopilot
  --confirmed-by <name>            default: owner
  --module-hints <csv>             default: requirements,implementation,testing,documentation
  --max-modules <n>                default: 6
  --strategy <speed|balanced|safe> default: balanced
  --execute <true|false>           default: true
  --force-redecompose <true|false> default: false
  --require-final-next-action <true|false>
                                  default: true
                                  true: next_action must be terminal (none/completed/done)
  --verify-cmd <command>           optional command gate; non-zero exit blocks completion
  --max-tasks <n>                  default: 0 (no limit)
  --max-retries <n>                default: 0 (retry forever per task)
  --retry-interval <seconds>       default: 5
  --strict                         fail on task error (default)
  --non-strict                     continue to next task on task error
  --dry-run                        print actions only
  -h, --help
EOF
}

POSITIONALS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan)
      PLAN_PATH="${2:-}"
      shift
      ;;
    --control-url)
      CONTROL_URL="${2:-}"
      shift
      ;;
    --report-root)
      REPORT_ROOT="${2:-}"
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
    --require-final-next-action)
      REQUIRE_FINAL_NEXT_ACTION="${2:-}"
      shift
      ;;
    --verify-cmd)
      VERIFY_CMD="${2:-}"
      shift
      ;;
    --max-tasks)
      MAX_TASKS="${2:-}"
      shift
      ;;
    --max-retries)
      MAX_RETRIES="${2:-}"
      shift
      ;;
    --retry-interval)
      RETRY_INTERVAL_SECONDS="${2:-}"
      shift
      ;;
    --strict)
      STRICT_MODE=true
      ;;
    --non-strict)
      STRICT_MODE=false
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
  PLAN_PATH="${POSITIONALS[0]}"
fi

if [[ -z "${PLAN_PATH}" || ! -f "${PLAN_PATH}" ]]; then
  echo "plan file not found: ${PLAN_PATH}"
  exit 1
fi

if ! [[ "${MAX_TASKS}" =~ ^[0-9]+$ ]]; then
  echo "invalid --max-tasks: ${MAX_TASKS}"
  exit 1
fi

if ! [[ "${MAX_RETRIES}" =~ ^[0-9]+$ ]]; then
  echo "invalid --max-retries: ${MAX_RETRIES}"
  exit 1
fi

if ! [[ "${RETRY_INTERVAL_SECONDS}" =~ ^[0-9]+$ ]]; then
  echo "invalid --retry-interval: ${RETRY_INTERVAL_SECONDS}"
  exit 1
fi

if ! [[ "${REQUIRE_FINAL_NEXT_ACTION}" =~ ^(true|false)$ ]]; then
  echo "invalid --require-final-next-action: ${REQUIRE_FINAL_NEXT_ACTION} (expected true|false)"
  exit 1
fi

plan_tool() {
  python3 - "${PLAN_PATH}" "$@" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

plan_path = Path(sys.argv[1])
cmd = sys.argv[2]
text = plan_path.read_text(encoding="utf-8")
lines = text.splitlines()


def in_current_sprint(idx: int) -> bool:
    seen = False
    for i, line in enumerate(lines):
        if i > idx:
            break
        if line.strip() == "## Current Sprint (Ordered)":
            seen = True
            continue
        if seen and line.startswith("## ") and i != idx:
            return False
    return seen


def parse_table_row(line: str) -> list[str] | None:
    striped = line.strip()
    if not (striped.startswith("|") and striped.endswith("|")):
        return None
    parts = [part.strip() for part in striped.split("|")[1:-1]]
    if len(parts) != 5:
        return None
    if parts[0] in {"ID", "---"}:
        return None
    if all(set(part) <= {"-"} for part in parts):
        return None
    return parts


def find_task_row(task_id: str) -> tuple[int, list[str]] | None:
    for idx, line in enumerate(lines):
        if not in_current_sprint(idx):
            continue
        row = parse_table_row(line)
        if row is None:
            continue
        if row[0] == task_id:
            return idx, row
    return None


def write_lines() -> None:
    plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if cmd == "next":
    for idx, line in enumerate(lines):
        if not in_current_sprint(idx):
            continue
        row = parse_table_row(line)
        if row is None:
            continue
        status = row[4].strip().lower()
        if status in {"planned", "doing"}:
            print(json.dumps({"id": row[0], "task": row[1], "status": row[4]}))
            raise SystemExit(0)
    print("")
    raise SystemExit(0)

if cmd == "set-status":
    task_id = sys.argv[3]
    new_status = sys.argv[4]
    found = find_task_row(task_id)
    if found is None:
        raise SystemExit(f"task not found in current sprint: {task_id}")
    idx, row = found
    row[4] = new_status
    lines[idx] = f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |"
    write_lines()
    raise SystemExit(0)

if cmd == "append-log":
    task_id = sys.argv[3]
    event = sys.argv[4]
    state = sys.argv[5]
    suffix = sys.argv[6] if len(sys.argv) > 6 else ""
    today = datetime.now().date().isoformat()
    log_key = f"DOC-{today}-{task_id}"
    line = f"- {today} `{log_key}` {event} (`{state}`)"
    if suffix:
        line = f"{line} {suffix}"
    if line in lines:
        raise SystemExit(0)

    insert_at = None
    for idx, raw in enumerate(lines):
        if raw.strip() == "## Task Log (Recent)":
            insert_at = idx + 1
            break

    if insert_at is None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("## Task Log (Recent)")
        lines.append("")
        lines.append(line)
    else:
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        lines.insert(insert_at, line)
    write_lines()
    raise SystemExit(0)

raise SystemExit(f"unknown cmd: {cmd}")
PY
}

safe_task_slug() {
  echo "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -cs 'a-z0-9' '-' \
    | sed -E 's/^-+//; s/-+$//; s/-+/-/g'
}

build_requirements_text() {
  local task_id="$1"
  local task_text="$2"
  python3 - "$task_id" "$task_text" <<'PY'
from __future__ import annotations

import sys

task_id = sys.argv[1].strip()
task_text = sys.argv[2].strip()
msg = (
    f"Execute PLAN task {task_id}: {task_text}. "
    "Mandatory order: update plan first, implement changes, run checks, update docs. "
    "Follow project rules from PLAN.md and AGENTS.md. "
    "Do not guess ambiguous requirements; request clarification when blocked."
)
print(msg)
PY
}

run_single_task() {
  local task_id="$1"
  local task_text="$2"
  local attempt="$3"

  local slug
  slug="$(safe_task_slug "${task_id}")"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local report_dir="${REPORT_ROOT}/${slug}"
  local latest_summary="${report_dir}/latest.json"
  local project_name="plan-auto-${slug}-${stamp}"
  local task_title="${task_id} ${task_text}"
  local requirements_text
  requirements_text="$(build_requirements_text "${task_id}" "${task_text}")"

  echo "[task=${task_id}] attempt=${attempt} project=${project_name}"
  echo "[task=${task_id}] requirements=${requirements_text}"

  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[dry-run] bash scripts/main_orchestrate.sh ${CONTROL_URL} --project-name ${project_name} --task-title ${task_title}"
    return 0
  fi

  mkdir -p "${report_dir}"
  MB3_DRY_RUN_PROJECT_NAME="${project_name}" \
    MB3_DRY_RUN_TASK_TITLE="${task_title}" \
    MB3_DRY_RUN_REQUIREMENTS="${requirements_text}" \
    MB3_DRY_RUN_MODULE_HINTS="${MODULE_HINTS}" \
    MB3_DRY_RUN_MAX_MODULES="${MAX_MODULES}" \
    MB3_DRY_RUN_STRATEGY="${STRATEGY}" \
    MB3_DRY_RUN_EXECUTE="${EXECUTE}" \
    MB3_DRY_RUN_FORCE_REDECOMPOSE="${FORCE_REDECOMPOSE}" \
    MB3_DRY_RUN_REQUESTED_BY="${REQUESTED_BY}" \
    MB3_DRY_RUN_CONFIRMED_BY="${CONFIRMED_BY}" \
    MB3_DRY_RUN_REPORT_DIR="${report_dir}" \
    MB3_DRY_RUN_LATEST_SUMMARY_PATH="${latest_summary}" \
    bash "${ROOT_DIR}/scripts/main_orchestrate.sh" "${CONTROL_URL}"

  if [[ ! -f "${latest_summary}" ]]; then
    TASK_FAIL_REASON="latest_summary_missing"
    echo "[task=${task_id}] latest summary missing: ${latest_summary}"
    return 2
  fi

  local command_status
  command_status="$(
    python3 - "${latest_summary}" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(payload.get("terminal_status", "")).strip())
PY
  )"
  local orchestration_status
  orchestration_status="$(
    python3 - "${latest_summary}" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
value = str(payload.get("orchestration_status", "")).strip()
if not value:
    value = str(payload.get("latest_orchestration_status", "")).strip()
print(value)
PY
  )"
  local next_action
  next_action="$(
    python3 - "${latest_summary}" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
value = str(payload.get("workflow_next_action", "")).strip()
if not value:
    value = str(payload.get("latest_next_action", "")).strip()
print(value)
PY
  )"

  echo "[task=${task_id}] command_status=${command_status} orchestration_status=${orchestration_status} next_action=${next_action:-none}"

  if [[ "${command_status}" != "success" ]]; then
    TASK_FAIL_REASON="terminal_status=${command_status:-unknown}"
    return 3
  fi

  if [[ ! "${orchestration_status}" =~ ^(executed|prepared)$ ]]; then
    TASK_FAIL_REASON="orchestration_status=${orchestration_status:-unknown}"
    return 4
  fi

  if [[ "${REQUIRE_FINAL_NEXT_ACTION}" == "true" ]]; then
    local normalized_next
    normalized_next="$(echo "${next_action}" | tr '[:upper:]' '[:lower:]' | tr -d ' ')"
    if [[ ! "${normalized_next}" =~ ^($|none|null|completed|done)$ ]]; then
      TASK_FAIL_REASON="next_action_pending:${next_action}"
      return 5
    fi
  fi

  if [[ -n "${VERIFY_CMD}" ]]; then
    echo "[task=${task_id}] verify_cmd=${VERIFY_CMD}"
    if ! bash -lc "${VERIFY_CMD}"; then
      TASK_FAIL_REASON="verify_cmd_failed"
      return 6
    fi
  fi

  TASK_FAIL_REASON=""
  return 0
}

executed=0

echo "plan_autopilot start"
echo "plan=${PLAN_PATH}"
echo "control_url=${CONTROL_URL}"
echo "max_tasks=${MAX_TASKS} max_retries=${MAX_RETRIES} retry_interval=${RETRY_INTERVAL_SECONDS}s strict=${STRICT_MODE}"
echo "done_gate require_final_next_action=${REQUIRE_FINAL_NEXT_ACTION} verify_cmd=${VERIFY_CMD:-none}"

while true; do
  if [[ "${MAX_TASKS}" -gt 0 && "${executed}" -ge "${MAX_TASKS}" ]]; then
    echo "max task limit reached: ${executed}"
    break
  fi

  next_json="$(plan_tool next)"
  if [[ -z "${next_json}" ]]; then
    echo "no planned/doing task left in current sprint"
    break
  fi

  task_id="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "${next_json}")"
  task_text="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["task"])' "${next_json}")"
  task_status="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["status"])' "${next_json}")"

  echo "next task: ${task_id} (${task_status})"

  if [[ "${DRY_RUN}" != "true" && "${task_status}" == "planned" ]]; then
    plan_tool set-status "${task_id}" "doing"
    plan_tool append-log "${task_id}" "started" "doing"
  fi

  attempt=1
  while true; do
    if run_single_task "${task_id}" "${task_text}" "${attempt}"; then
      if [[ "${DRY_RUN}" != "true" ]]; then
        plan_tool set-status "${task_id}" "done"
        plan_tool append-log "${task_id}" "completed" "done"
      fi
      executed=$((executed + 1))
      break
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
      echo "[dry-run] task failed simulation; stop after first task."
      exit 1
    fi

    blocker_note="(blocked: attempt=${attempt}, reason=${TASK_FAIL_REASON:-unknown}, check ${REPORT_ROOT}/$(safe_task_slug "${task_id}")/latest.json)"
    plan_tool append-log "${task_id}" "blocked" "doing" "${blocker_note}"

    if [[ "${MAX_RETRIES}" -gt 0 && "${attempt}" -ge "${MAX_RETRIES}" ]]; then
      echo "[task=${task_id}] retry exhausted (${MAX_RETRIES})"
      if [[ "${STRICT_MODE}" == "true" ]]; then
        exit 1
      fi
      executed=$((executed + 1))
      break
    fi

    attempt=$((attempt + 1))
    echo "[task=${task_id}] retry in ${RETRY_INTERVAL_SECONDS}s (attempt=${attempt})"
    sleep "${RETRY_INTERVAL_SECONDS}"
  done
done

echo "plan_autopilot done (executed=${executed})"
