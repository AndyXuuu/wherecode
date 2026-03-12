#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBPROJECT_KEY="stock-sentiment"
LATEST_REPORT_PATH=""
REPORT_PATH=""

usage() {
  cat <<'EOF_USAGE'
Usage:
  bash scripts/v2_gate.sh [options]

Options:
  --subproject <key>      default: stock-sentiment
  --latest <path>         default: docs/v2_reports/latest_<subproject>_v2_run.json
  --report <path>         explicit report file (skip latest pointer lookup)
  -h, --help
EOF_USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subproject)
      SUBPROJECT_KEY="${2:-}"
      shift
      ;;
    --latest)
      LATEST_REPORT_PATH="${2:-}"
      shift
      ;;
    --report)
      REPORT_PATH="${2:-}"
      shift
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

if [[ -z "${REPORT_PATH}" ]]; then
  if [[ -z "${LATEST_REPORT_PATH}" ]]; then
    LATEST_REPORT_PATH="${ROOT_DIR}/docs/v2_reports/latest_${SUBPROJECT_KEY}_v2_run.json"
  fi
  if [[ ! -f "${LATEST_REPORT_PATH}" ]]; then
    echo "v2_gate failed: latest report not found: ${LATEST_REPORT_PATH}"
    exit 1
  fi
else
  if [[ ! -f "${REPORT_PATH}" ]]; then
    echo "v2_gate failed: report not found: ${REPORT_PATH}"
    exit 1
  fi
fi

python3 - "${ROOT_DIR}" "${SUBPROJECT_KEY}" "${LATEST_REPORT_PATH}" "${REPORT_PATH}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

root_dir = Path(sys.argv[1]).resolve()
expected_subproject = (sys.argv[2] or "").strip()
latest_path_arg = (sys.argv[3] or "").strip()
report_path_arg = (sys.argv[4] or "").strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


errors: list[str] = []
warnings: list[str] = []

source_latest_path: Path | None = None
source_report_path: Path
payload: dict[str, Any]

if report_path_arg:
    source_report_path = resolve_path(Path.cwd(), report_path_arg)
    payload = read_json(source_report_path)
else:
    source_latest_path = resolve_path(Path.cwd(), latest_path_arg)
    latest_payload = read_json(source_latest_path)
    report_path_value = str(latest_payload.get("report_path") or "").strip()
    if report_path_value:
        source_report_path = resolve_path(source_latest_path.parent, report_path_value)
        if not source_report_path.exists():
            errors.append(f"report_path target missing: {source_report_path}")
            payload = latest_payload
        else:
            payload = read_json(source_report_path)
    else:
        source_report_path = source_latest_path
        payload = latest_payload

version = str(payload.get("version") or "").strip().lower()
if version != "v2":
    errors.append(f"version must be 'v2' (got: {version or '<empty>'})")

run = payload.get("run")
if not isinstance(run, dict):
    errors.append("run section missing or invalid")
    run = {}

run_subproject = str(run.get("subproject_key") or "").strip()
if not run_subproject:
    errors.append("run.subproject_key is required")
elif expected_subproject and run_subproject != expected_subproject:
    errors.append(
        f"run.subproject_key mismatch: expected '{expected_subproject}', got '{run_subproject}'"
    )

run_mode = str(run.get("mode") or "").strip().lower()
if run_mode not in {"plan", "build"}:
    errors.append(f"run.mode must be plan|build (got: {run_mode or '<empty>'})")

workflow_mode = str(run.get("workflow_mode") or "test").strip().lower()
if workflow_mode not in {"test", "dev"}:
    errors.append(
        f"run.workflow_mode must be test|dev (got: {workflow_mode or '<empty>'})"
    )

run_status = str(run.get("final_status") or "").strip().lower()
if run_status not in {"success", "succeeded"}:
    errors.append(
        f"run.final_status must be success|succeeded (got: {run_status or '<empty>'})"
    )

input_section = payload.get("input")
if not isinstance(input_section, dict):
    errors.append("input section missing or invalid")
    input_section = {}

requirements = str(input_section.get("requirements") or "").strip()
if not requirements:
    errors.append("input.requirements is empty")

requirement_file = str(input_section.get("requirement_file") or "").strip()
if not requirement_file:
    errors.append("input.requirement_file is empty")
else:
    requirement_path = resolve_path(root_dir, requirement_file)
    if not requirement_path.exists():
        warnings.append(f"input.requirement_file not found on disk: {requirement_path}")

benchmark = payload.get("benchmark")
if not isinstance(benchmark, dict):
    errors.append("benchmark section missing or invalid")
    benchmark = {}
targets = benchmark.get("targets")
if not isinstance(targets, list):
    errors.append("benchmark.targets must be a list")
    targets = []
target_set = {str(item).strip().lower() for item in targets if str(item).strip()}
for expected_target in ("openclaw", "opencode", "oh-my-opencode"):
    if expected_target not in target_set:
        errors.append(f"benchmark.targets missing: {expected_target}")

outputs = payload.get("outputs")
if not isinstance(outputs, dict):
    outputs = {}

if run_mode == "build":
    full_cycle_status = str(outputs.get("full_cycle_status") or "").strip().lower()
    if workflow_mode == "dev":
        if full_cycle_status not in {"success", "succeeded", "in_progress"}:
            errors.append(
                "outputs.full_cycle_status must be success|succeeded|in_progress for build mode with workflow_mode=dev"
            )
    else:
        if full_cycle_status not in {"success", "succeeded"}:
            errors.append(
                "outputs.full_cycle_status must be success|succeeded for build mode"
            )

logs = payload.get("logs")
if not isinstance(logs, dict):
    warnings.append("logs section missing or invalid")
else:
    plan_output = str(logs.get("plan_output") or "").strip()
    build_output = str(logs.get("build_output") or "").strip()
    if not plan_output and not build_output:
        warnings.append("both logs.plan_output and logs.build_output are empty")

diagnosis = payload.get("diagnosis")
if not isinstance(diagnosis, dict):
    errors.append("diagnosis section missing or invalid")
    diagnosis = {}

failure_taxonomy = diagnosis.get("failure_taxonomy")
if not isinstance(failure_taxonomy, dict):
    errors.append("diagnosis.failure_taxonomy missing or invalid")
    failure_taxonomy = {}

taxonomy_code = str(failure_taxonomy.get("code") or "").strip().lower()
taxonomy_stage = str(failure_taxonomy.get("stage") or "").strip().lower()
taxonomy_severity = str(failure_taxonomy.get("severity") or "").strip().lower()
taxonomy_reason = str(failure_taxonomy.get("reason") or "").strip()

if not taxonomy_code:
    errors.append("diagnosis.failure_taxonomy.code is required")
if not taxonomy_stage:
    errors.append("diagnosis.failure_taxonomy.stage is required")
if not taxonomy_severity:
    errors.append("diagnosis.failure_taxonomy.severity is required")
if not taxonomy_reason:
    errors.append("diagnosis.failure_taxonomy.reason is required")

retry_hints = diagnosis.get("retry_hints")
if not isinstance(retry_hints, list):
    errors.append("diagnosis.retry_hints must be a list")
    retry_hints = []
elif run_status in {"failed", "error"} and len(retry_hints) == 0:
    errors.append("diagnosis.retry_hints must not be empty for failed run")

next_commands = diagnosis.get("next_commands")
if not isinstance(next_commands, list):
    warnings.append("diagnosis.next_commands should be a list")
else:
    if run_status in {"failed", "error"} and len(next_commands) == 0:
        warnings.append("diagnosis.next_commands is empty for failed run")

if run_status in {"success", "succeeded"} and taxonomy_code != "success":
    errors.append(
        "diagnosis.failure_taxonomy.code must be success when run.final_status is success"
    )
if run_status in {"failed", "error"} and taxonomy_code == "success":
    errors.append(
        "diagnosis.failure_taxonomy.code must not be success when run.final_status is failed"
    )

status = "pass" if not errors else "fail"
print(f"v2_gate={status}")
if source_latest_path is not None:
    print(f"latest_report={source_latest_path}")
print(f"report={source_report_path}")
print(f"subproject={run_subproject or '<unknown>'}")
print(f"mode={run_mode or '<unknown>'}")
print(f"final_status={run_status or '<unknown>'}")

if warnings:
    for warning in warnings:
        print(f"warning: {warning}")

if errors:
    for error in errors:
        print(f"error: {error}")
    sys.exit(1)
PY

echo "v2_gate checks passed"
