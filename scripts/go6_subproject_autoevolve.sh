#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBPROJECT_KEY="${1:-stock-sentiment}"
STAMP="${2:-$(date -u +%Y%m%dT%H%M%SZ)}"

SUBPROJECT_DIR="${ROOT_DIR}/project/${SUBPROJECT_KEY}"
CONFIG_PATH="${SUBPROJECT_DIR}/evolve.json"
DEFAULT_REQUIREMENTS="build stock sentiment pipeline with opinion crawl, sentiment scoring, value assessment, industry analysis, theme analysis, and risk summary output"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/go6_subproject_autoevolve.sh [subproject_key] [stamp]

Compatibility mode:
- delegates to local no-model full cycle runner
- keeps command path stable for check/evolve entry
USAGE
}

if [[ "${SUBPROJECT_KEY}" == "-h" || "${SUBPROJECT_KEY}" == "--help" || "${SUBPROJECT_KEY}" == "help" ]]; then
  usage
  exit 0
fi

requirements="${DEFAULT_REQUIREMENTS}"
if [[ -f "${CONFIG_PATH}" ]]; then
  maybe_requirements="$({
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
  if [[ -n "${maybe_requirements}" ]]; then
    requirements="${maybe_requirements}"
  fi
fi

bash "${ROOT_DIR}/scripts/go8_subproject_full_cycle.sh" "${SUBPROJECT_KEY}" \
  --requirements "${requirements}" \
  --force-clean false \
  --stamp "${STAMP}"

echo "go6 compatibility run done: key=${SUBPROJECT_KEY} stamp=${STAMP}"
