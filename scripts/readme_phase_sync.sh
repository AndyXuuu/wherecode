#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN_PATH="${README_PHASE_SYNC_PLAN_PATH:-${ROOT_DIR}/PLAN.md}"
README_PATH="${README_PHASE_SYNC_README_PATH:-${ROOT_DIR}/README.MD}"
SUMMARY_PATH="${README_PHASE_SYNC_SUMMARY_PATH:-${ROOT_DIR}/docs/ops_reports/latest_tst2_t2_release_rehearsal.json}"
DRY_RUN=false
STRICT_MODE=false

usage() {
  cat <<'EOF'
Usage:
  bash scripts/readme_phase_sync.sh [--dry-run] [--strict]

Options:
  --dry-run  print generated section only, do not write README
  --strict   exit non-zero on missing required files/sections
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      ;;
    --strict)
      STRICT_MODE=true
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

if [[ ! -f "${PLAN_PATH}" ]]; then
  echo "plan_missing=true path=${PLAN_PATH}"
  if [[ "${STRICT_MODE}" == "true" ]]; then
    exit 1
  fi
  exit 0
fi

if [[ ! -f "${README_PATH}" ]]; then
  echo "readme_missing=true path=${README_PATH}"
  if [[ "${STRICT_MODE}" == "true" ]]; then
    exit 1
  fi
  exit 0
fi

python3 - "${PLAN_PATH}" "${README_PATH}" "${SUMMARY_PATH}" "${DRY_RUN}" "${STRICT_MODE}" <<'PY'
import json
import sys
from pathlib import Path

plan_path = Path(sys.argv[1])
readme_path = Path(sys.argv[2])
summary_path = Path(sys.argv[3])
dry_run = sys.argv[4].lower() == "true"
strict_mode = sys.argv[5].lower() == "true"


def parse_table(markdown: str, section_prefix: str):
    lines = markdown.splitlines()
    start_idx = None
    for idx, line in enumerate(lines):
        if line.startswith(section_prefix):
            start_idx = idx
            break
    if start_idx is None:
        return []

    table_lines = []
    cursor = start_idx + 1
    while cursor < len(lines):
        current = lines[cursor].strip()
        if current.startswith("|"):
            table_lines.append(current)
            cursor += 1
            continue
        if table_lines:
            break
        cursor += 1

    if len(table_lines) < 3:
        return []

    headers = [item.strip() for item in table_lines[0].strip("|").split("|")]
    rows = []
    for raw in table_lines[2:]:
        cols = [item.strip() for item in raw.strip("|").split("|")]
        if len(cols) < len(headers):
            continue
        rows.append(dict(zip(headers, cols)))
    return rows


def status_done(status: str) -> bool:
    normalized = status.strip().lower()
    return normalized in {"done", "passed", "complete", "completed"}


def normalize_sentence(text: str) -> str:
    value = text.strip()
    if not value:
        return value
    if value.endswith("."):
        return value
    return value + "."


def stage_text(stage: str, goal: str) -> str:
    predefined = {
        "M-TEST-ENTRY": "milestone gate passed",
        "TST1": "integration matrix + rollback/policy regression completed",
        "TST2": "stability hardening + release rehearsal completed",
        "REL1": "release package and signoff",
        "GO1": "single-host launch checklist",
    }
    return normalize_sentence(predefined.get(stage, goal or stage))


plan_text = plan_path.read_text(encoding="utf-8")
readme_text = readme_path.read_text(encoding="utf-8")

active_rows = parse_table(plan_text, "## 2) Active Sprint")
release_rows = parse_table(plan_text, "## 3) Release Map")

release_by_stage = {}
for row in release_rows:
    stage = row.get("Stage", "").strip()
    if stage:
        release_by_stage[stage] = row

rehearsal_note = ""
if summary_path.exists():
    try:
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        overall_passed = bool(summary_data.get("overall_passed"))
        checkpoint_guard = bool(summary_data.get("checkpoint_guard_passed"))
        overall_label = "passed" if overall_passed else "failed"
        checkpoint_label = "passed" if checkpoint_guard else "failed"
        rehearsal_note = f"latest rehearsal {overall_label}, checkpoint {checkpoint_label}"
    except Exception:
        rehearsal_note = ""

completed_items = [
    "- [x] `K1-K50`: workflow orchestration, role pipeline, policy gates, state persistence."
]
planned_items = []
seen_completed = {"K1-K50"}
seen_planned = set()

for stage in ("M-TEST-ENTRY", "TST1", "TST2", "REL1", "GO1"):
    row = release_by_stage.get(stage)
    if not row:
        continue
    status = row.get("Status", "")
    text = stage_text(stage, row.get("Goal", ""))
    if status_done(status):
        if stage not in seen_completed:
            completed_items.append(f"- [x] `{stage}`: {text}")
            seen_completed.add(stage)
    elif stage in {"REL1", "GO1"} and stage not in seen_planned:
        planned_items.append(f"- [ ] `{stage}`: {text}")
        seen_planned.add(stage)

for row in active_rows:
    task_id = row.get("ID", "").strip()
    task_name = normalize_sentence(row.get("Task", ""))
    status = row.get("Status", "")
    if not task_id or not task_name:
        continue

    if status_done(status):
        if task_id not in seen_completed:
            completed_items.append(f"- [x] `{task_id}`: {task_name}")
            seen_completed.add(task_id)
        continue

    if task_id in seen_planned:
        continue
    if task_id == "TST2-T2" and rehearsal_note:
        planned_items.append(f"- [ ] `{task_id}`: {task_name[:-1]} ({rehearsal_note}).")
    else:
        planned_items.append(f"- [ ] `{task_id}`: {task_name}")
    seen_planned.add(task_id)

if not planned_items:
    planned_items = ["- [ ] `REL1`: release package and signoff."]

start_marker = "## 📅 Plan & Completed Phases"
start = readme_text.find(start_marker)
if start < 0:
    print("readme_phase_section_missing=true")
    if strict_mode:
        sys.exit(1)
    sys.exit(0)

tail = readme_text[start:]
after_start = tail.find("\n---")
if after_start < 0:
    print("readme_phase_section_end_missing=true")
    if strict_mode:
        sys.exit(1)
    sys.exit(0)

section_end = start + after_start + len("\n---")
new_section = "\n".join(
    [
        "## 📅 Plan & Completed Phases",
        "",
        "### Completed",
        "",
        *completed_items,
        "",
        "### Plan",
        "",
        *planned_items,
        "",
        "---",
    ]
)
new_readme = readme_text[:start] + new_section + readme_text[section_end:]

if dry_run:
    print(new_section)
else:
    readme_path.write_text(new_readme, encoding="utf-8")

print(f"readme_phase_sync_updated=true")
print(f"readme_path={readme_path}")
print(f"completed_total={len(completed_items)}")
print(f"plan_total={len(planned_items)}")
if rehearsal_note:
    print(f"rehearsal_note={rehearsal_note}")
PY
