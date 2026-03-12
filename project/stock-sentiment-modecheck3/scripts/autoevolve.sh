#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${DIR}/evolve.json"
REPORT_DIR="${DIR}/reports"
LATEST_SEED_PATH="${REPORT_DIR}/latest_seed.json"
LATEST_AUTO_PATH="${REPORT_DIR}/latest_autoevolve.json"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
AUTO_REPORT="${REPORT_DIR}/${STAMP}-autoevolve.json"

if [[ ! -f "${LATEST_SEED_PATH}" ]]; then
  echo "missing ${LATEST_SEED_PATH}; run seed.sh first"
  exit 1
fi

python3 -m py_compile "${DIR}/backend/app/models.py" "${DIR}/backend/app/analyzer.py" "${DIR}/backend/app/main.py"
PYTHONPATH="${DIR}/backend" python3 -m unittest discover -s "${DIR}/backend/tests" -p 'test_*.py' >/dev/null

python3 - "${CONFIG_PATH}" "${AUTO_REPORT}" "${LATEST_AUTO_PATH}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

config_path, auto_report_path, latest_path = sys.argv[1:]
config = json.loads(Path(config_path).read_text(encoding="utf-8"))

sys.path.insert(0, str(Path(config_path).parent / "backend"))
from app.analyzer import analyze_text  # type: ignore

sample_text = (
    f"{config.get('requirements', '')} "
    "Nvidia reports strong chip demand with record growth and profit."
)
sample_result = analyze_text(sample_text)

summary = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "mode": "local_rule_engine",
    "run_id": datetime.now(timezone.utc).strftime("local_%Y%m%dT%H%M%SZ"),
    "final_status": "succeeded",
    "sample_result": sample_result,
}
Path(auto_report_path).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "run_id": summary["run_id"],
    "final_status": summary["final_status"],
    "mode": summary["mode"],
    "report_path": str(Path(auto_report_path).resolve()),
}
Path(latest_path).write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(str(Path(auto_report_path)))
print(json.dumps({"run_id": latest["run_id"], "final_status": latest["final_status"], "mode": latest["mode"]}, ensure_ascii=False))
PY
