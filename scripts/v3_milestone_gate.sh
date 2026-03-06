#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MILESTONE="test-entry"
STRICT=false
STATE_FILE="${WHERECODE_STATE_FILE:-${ROOT_DIR}/.wherecode/state.json}"
MILESTONE_FILE="${WHERECODE_MILESTONE_FILE:-${ROOT_DIR}/.wherecode/milestones.json}"
REPORT_DIR="${SOAK_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
SOAK_SAMPLES_FILE="${TST2_SOAK_SAMPLES_FILE:-}"
TST2_SUMMARY_FILE="${TST2_REHEARSAL_SUMMARY_FILE:-${REPORT_DIR}/latest_tst2_t2_release_rehearsal.json}"
TST2_MIN_SAMPLES="${TST2_MIN_SAMPLES:-288}"
TST2_DURATION_SECONDS="${TST2_DURATION_SECONDS:-86400}"
TST2_INTERVAL_SECONDS="${TST2_INTERVAL_SECONDS:-300}"
TST2_MAX_FAILED_RUN_DELTA="${TST2_MAX_FAILED_RUN_DELTA:-0}"
TST2_MAX_PROBE_FAILED_ROUNDS="${TST2_MAX_PROBE_FAILED_ROUNDS:-0}"
TST2_PROFILE="${TST2_PROFILE:-full}"

SET_TST2_MIN_SAMPLES=0
SET_TST2_DURATION_SECONDS=0
SET_TST2_INTERVAL_SECONDS=0
SET_TST2_MAX_FAILED_RUN_DELTA=0
SET_TST2_MAX_PROBE_FAILED_ROUNDS=0

usage() {
  cat <<'EOF'
usage: bash scripts/v3_milestone_gate.sh [options]

Options:
  --milestone <test-entry|tst2-ready>
  --strict
  --state-file <path>
  --milestone-file <path>
  --soak-samples-file <path>
  --tst2-summary-file <path>
  --tst2-min-samples <n>
  --tst2-duration-seconds <n>
  --tst2-interval-seconds <n>
  --tst2-max-failed-run-delta <n>
  --tst2-max-probe-failed-rounds <n>
  --tst2-profile <full|local>
EOF
}

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
    --soak-samples-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --soak-samples-file"
        exit 1
      fi
      SOAK_SAMPLES_FILE="$1"
      ;;
    --tst2-summary-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --tst2-summary-file"
        exit 1
      fi
      TST2_SUMMARY_FILE="$1"
      ;;
    --tst2-min-samples)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --tst2-min-samples"
        exit 1
      fi
      TST2_MIN_SAMPLES="$1"
      SET_TST2_MIN_SAMPLES=1
      ;;
    --tst2-duration-seconds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --tst2-duration-seconds"
        exit 1
      fi
      TST2_DURATION_SECONDS="$1"
      SET_TST2_DURATION_SECONDS=1
      ;;
    --tst2-interval-seconds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --tst2-interval-seconds"
        exit 1
      fi
      TST2_INTERVAL_SECONDS="$1"
      SET_TST2_INTERVAL_SECONDS=1
      ;;
    --tst2-max-failed-run-delta)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --tst2-max-failed-run-delta"
        exit 1
      fi
      TST2_MAX_FAILED_RUN_DELTA="$1"
      SET_TST2_MAX_FAILED_RUN_DELTA=1
      ;;
    --tst2-max-probe-failed-rounds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --tst2-max-probe-failed-rounds"
        exit 1
      fi
      TST2_MAX_PROBE_FAILED_ROUNDS="$1"
      SET_TST2_MAX_PROBE_FAILED_ROUNDS=1
      ;;
    --tst2-profile)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --tst2-profile"
        exit 1
      fi
      TST2_PROFILE="$1"
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

if [[ "${TST2_PROFILE}" != "full" && "${TST2_PROFILE}" != "local" ]]; then
  echo "unsupported --tst2-profile: ${TST2_PROFILE}"
  exit 1
fi

if [[ "${TST2_PROFILE}" == "local" ]]; then
  if [[ "${SET_TST2_MIN_SAMPLES}" -eq 0 ]]; then
    TST2_MIN_SAMPLES=12
  fi
  if [[ "${SET_TST2_DURATION_SECONDS}" -eq 0 ]]; then
    TST2_DURATION_SECONDS=2400
  fi
  if [[ "${SET_TST2_INTERVAL_SECONDS}" -eq 0 ]]; then
    TST2_INTERVAL_SECONDS=300
  fi
  if [[ "${SET_TST2_MAX_FAILED_RUN_DELTA}" -eq 0 ]]; then
    TST2_MAX_FAILED_RUN_DELTA=0
  fi
  if [[ "${SET_TST2_MAX_PROBE_FAILED_ROUNDS}" -eq 0 ]]; then
    TST2_MAX_PROBE_FAILED_ROUNDS=0
  fi
fi

python3 - "${MILESTONE}" "${STRICT}" "${STATE_FILE}" "${MILESTONE_FILE}" "${REPORT_DIR}" "${SOAK_SAMPLES_FILE}" "${TST2_SUMMARY_FILE}" "${TST2_MIN_SAMPLES}" "${TST2_DURATION_SECONDS}" "${TST2_INTERVAL_SECONDS}" "${TST2_MAX_FAILED_RUN_DELTA}" "${TST2_MAX_PROBE_FAILED_ROUNDS}" "${TST2_PROFILE}" <<'PY'
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
report_dir = Path(sys.argv[5]).expanduser()
soak_samples_file = Path(sys.argv[6]).expanduser() if sys.argv[6].strip() else None
tst2_summary_file = Path(sys.argv[7]).expanduser()
tst2_min_samples = int(sys.argv[8])
tst2_duration_seconds = int(sys.argv[9])
tst2_interval_seconds = int(sys.argv[10])
tst2_max_failed_run_delta = int(sys.argv[11])
tst2_max_probe_failed_rounds = int(sys.argv[12])
tst2_profile = sys.argv[13].strip() or "full"


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


def parse_iso_utc(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def load_soak_rows(samples_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    try:
        lines = samples_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def pick_default_soak_samples_file() -> Path | None:
    best_path: Path | None = None
    best_rows = -1
    best_mtime = -1.0
    for candidate in report_dir.glob("*-tst2-soak-samples.jsonl"):
        rows_count = len(load_soak_rows(candidate))
        try:
            mtime = candidate.stat().st_mtime
        except OSError:
            mtime = -1.0
        if rows_count > best_rows or (rows_count == best_rows and mtime > best_mtime):
            best_path = candidate
            best_rows = rows_count
            best_mtime = mtime
    return best_path


def evaluate_test_entry() -> dict[str, object]:
    if not state_file.exists():
        raise SystemExit(f"state file missing: {state_file}")

    try:
        state_payload = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid state-file json: {state_file}") from exc

    if not isinstance(state_payload, dict):
        raise SystemExit(f"invalid state-file payload: {state_file}")

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
    return payload


def evaluate_tst2_ready() -> dict[str, object]:
    samples_path = soak_samples_file
    if samples_path is None:
        samples_path = pick_default_soak_samples_file()

    rows: list[dict[str, object]] = []
    if samples_path and samples_path.exists():
        rows = load_soak_rows(samples_path)

    samples_total = len(rows)
    first_sampled_at = str(rows[0].get("sampled_at")) if rows else ""
    last_sampled_at = str(rows[-1].get("sampled_at")) if rows else ""
    latest_round = int(rows[-1].get("round", samples_total)) if rows else 0
    failed_start = int(rows[0].get("failed_run_count", 0)) if rows else 0
    failed_end = int(rows[-1].get("failed_run_count", 0)) if rows else 0
    failed_delta = failed_end - failed_start
    probe_failed_rounds = sum(1 for row in rows if str(row.get("probe_status")) == "failed")

    coverage_seconds = 0
    if rows and first_sampled_at and last_sampled_at:
        try:
            coverage_seconds = int((parse_iso_utc(last_sampled_at) - parse_iso_utc(first_sampled_at)).total_seconds())
        except Exception:
            coverage_seconds = 0

    required_coverage_seconds = max(0, tst2_duration_seconds - tst2_interval_seconds)
    summary_payload: dict[str, object] = {}
    if tst2_summary_file.exists():
        try:
            loaded = json.loads(tst2_summary_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                summary_payload = loaded
        except json.JSONDecodeError:
            summary_payload = {}

    rehearsal_overall_passed = bool(summary_payload.get("overall_passed"))
    rehearsal_checkpoint_guard_passed = bool(summary_payload.get("checkpoint_guard_passed"))

    checks = {
        "soak_samples_found": samples_total > 0,
        "soak_samples_reached_minimum": samples_total >= tst2_min_samples,
        "soak_coverage_reached_seconds": coverage_seconds >= required_coverage_seconds,
        "soak_failed_run_delta_within_limit": failed_delta <= tst2_max_failed_run_delta,
        "soak_probe_failures_within_limit": probe_failed_rounds <= tst2_max_probe_failed_rounds,
        "rehearsal_summary_found": bool(summary_payload),
        "rehearsal_overall_passed": rehearsal_overall_passed,
        "rehearsal_checkpoint_guard_passed": rehearsal_checkpoint_guard_passed,
    }
    passed = all(checks.values())
    missing_checks = [name for name, ok in checks.items() if not ok]

    payload = {
        "version": 1,
        "milestone": milestone,
        "status": "passed" if passed else "blocked",
        "passed": passed,
        "strict": strict,
        "updated_at": datetime.now().astimezone().isoformat(),
        "checks": checks,
        "required": {
            "tst2_profile": tst2_profile,
            "tst2_min_samples": tst2_min_samples,
            "tst2_duration_seconds": tst2_duration_seconds,
            "tst2_interval_seconds": tst2_interval_seconds,
            "tst2_required_coverage_seconds": required_coverage_seconds,
            "tst2_max_failed_run_delta": tst2_max_failed_run_delta,
            "tst2_max_probe_failed_rounds": tst2_max_probe_failed_rounds,
            "rehearsal_overall_passed": True,
            "rehearsal_checkpoint_guard_passed": True,
        },
        "observed": {
            "soak_samples_file": str(samples_path) if samples_path else None,
            "samples_total": samples_total,
            "latest_round": latest_round,
            "first_sampled_at": first_sampled_at or None,
            "last_sampled_at": last_sampled_at or None,
            "coverage_seconds": coverage_seconds,
            "failed_run_count_delta": failed_delta,
            "probe_failed_rounds": probe_failed_rounds,
            "rehearsal_summary_file": str(tst2_summary_file),
            "rehearsal_overall_passed": rehearsal_overall_passed,
            "rehearsal_checkpoint_guard_passed": rehearsal_checkpoint_guard_passed,
            "tst2_profile": tst2_profile,
        },
        "next_phase": "REL1" if passed else None,
        "recommended_next_action": (
            "promote to REL1 release signoff"
            if passed
            else "continue soak accumulation and rerun strict rehearsal gate"
        ),
        "summary": (
            (
                "milestone passed: TST2 readiness reached"
                if tst2_profile == "full"
                else "milestone passed: TST2 local readiness reached"
            )
            if passed
            else f"milestone blocked: {','.join(missing_checks)}"
        ),
    }
    if missing_checks:
        payload["missing_checks"] = missing_checks
    return payload


if milestone == "test-entry":
    payload = evaluate_test_entry()
elif milestone == "tst2-ready":
    payload = evaluate_tst2_ready()
else:
    raise SystemExit(f"unsupported milestone: {milestone}")

milestone_file.parent.mkdir(parents=True, exist_ok=True)
milestone_file.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(payload, ensure_ascii=False))

if strict and not bool(payload.get("passed")):
    raise SystemExit(1)
PY
