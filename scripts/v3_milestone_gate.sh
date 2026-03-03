#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MILESTONE="test-entry"
STRICT=false
STATE_FILE="${WHERECODE_STATE_FILE:-${ROOT_DIR}/.wherecode/state.json}"
MILESTONE_FILE="${WHERECODE_MILESTONE_FILE:-${ROOT_DIR}/.wherecode/milestones.json}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --milestone)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --milestone"
        exit 1
      fi
      MILESTONE="$1"
      ;;
    --strict)
      STRICT=true
      ;;
    --state-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --state-file"
        exit 1
      fi
      STATE_FILE="$1"
      ;;
    --milestone-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --milestone-file"
        exit 1
      fi
      MILESTONE_FILE="$1"
      ;;
    *)
      echo "unknown option: $1"
      echo "usage: bash scripts/v3_milestone_gate.sh [--milestone test-entry] [--strict] [--state-file <path>] [--milestone-file <path>]"
      exit 1
      ;;
  esac
  shift
done

python3 - "${MILESTONE}" "${STRICT}" "${STATE_FILE}" "${MILESTONE_FILE}" <<'PY'
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

milestone = sys.argv[1].strip()
strict = sys.argv[2].strip().lower() == "true"
state_file = Path(sys.argv[3]).expanduser()
milestone_file = Path(sys.argv[4]).expanduser()

if milestone != "test-entry":
    raise SystemExit(f"unsupported milestone: {milestone}")

if not state_file.exists():
    raise SystemExit(f"state file missing: {state_file}")

try:
    state_payload = json.loads(state_file.read_text(encoding="utf-8"))
except json.JSONDecodeError as exc:
    raise SystemExit(f"invalid state-file json: {state_file}") from exc

if not isinstance(state_payload, dict):
    raise SystemExit(f"invalid state-file payload: {state_file}")


def parse_task(raw: str | None) -> tuple[int, int] | None:
    if raw is None:
        return None
    match = re.fullmatch(r"K(\d+)-T(\d+)", raw.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)))


def parse_sprint(raw: str | None) -> int | None:
    if raw is None:
        return None
    match = re.fullmatch(r"K(\d+)", raw.strip())
    if match is None:
        return None
    return int(match.group(1))


last_completed_task = parse_task(str(state_payload.get("last_completed_task", "")).strip())
current_sprint = parse_sprint(str(state_payload.get("current_sprint", "")).strip())
current_sprint_raw = str(state_payload.get("current_sprint", "")).strip()
is_test_sprint = re.fullmatch(r"TST\d+", current_sprint_raw) is not None
last_verified_command = str(state_payload.get("last_verified_command", "")).strip()

checks = {
    "last_completed_task_at_least_k49_t3": bool(
        last_completed_task is not None
        and (
            last_completed_task[0] > 49
            or (last_completed_task[0] == 49 and last_completed_task[1] >= 3)
        )
    ),
    "current_sprint_at_least_k50": bool(
        is_test_sprint or (current_sprint is not None and current_sprint >= 50)
    ),
    "full_pytest_verified": last_verified_command == "control_center/.venv/bin/pytest -q",
}

passed = all(checks.values())
missing_checks = [name for name, ok in checks.items() if not ok]

payload: dict[str, object] = {
    "version": 1,
    "milestone": milestone,
    "status": "passed" if passed else "blocked",
    "passed": passed,
    "strict": strict,
    "updated_at": datetime.now().astimezone().isoformat(),
    "state_file": str(state_file),
    "checks": checks,
    "required": {
        "last_completed_task": ">= K49-T3",
        "current_sprint": ">= K50",
        "last_verified_command": "control_center/.venv/bin/pytest -q",
    },
    "next_phase": "TEST-PHASE" if passed else None,
    "recommended_next_action": (
        "start test sprint TST1"
        if passed
        else "finish delivery gates then rerun milestone gate"
    ),
    "summary": (
        "milestone passed: ready to enter test phase"
        if passed
        else f"milestone blocked: {','.join(missing_checks)}"
    ),
}

if missing_checks:
    payload["missing_checks"] = missing_checks

milestone_file.parent.mkdir(parents=True, exist_ok=True)
milestone_file.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(payload, ensure_ascii=False))

if strict and not passed:
    raise SystemExit(1)
PY
