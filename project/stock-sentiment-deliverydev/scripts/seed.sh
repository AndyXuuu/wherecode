#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${DIR}/evolve.json"
REPORT_DIR="${DIR}/reports"
LATEST_SUMMARY_PATH="${REPORT_DIR}/latest_seed.json"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "missing config: ${CONFIG_PATH}"
  exit 1
fi

mkdir -p "${REPORT_DIR}"
report_path="${REPORT_DIR}/${STAMP}-seed.json"

python3 - "${CONFIG_PATH}" "${report_path}" "${LATEST_SUMMARY_PATH}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

config_path, report_path, latest_path = sys.argv[1:]
payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
report = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "mode": "local_rule_engine",
    "status": "seeded",
    "project_name_prefix": payload.get("project_name_prefix"),
    "requirements": payload.get("requirements"),
    "module_hints": payload.get("module_hints"),
    "max_modules": payload.get("max_modules"),
    "strategy": payload.get("strategy"),
}
Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest = {"updated_at": datetime.now(timezone.utc).isoformat(), "report_path": str(Path(report_path).resolve()), **report}
Path(latest_path).write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

echo "report_written=${report_path}"
echo "latest_summary=${LATEST_SUMMARY_PATH}"
