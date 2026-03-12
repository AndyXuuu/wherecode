#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"

bash "${DIR}/scripts/check.sh"
bash "${DIR}/scripts/seed.sh" "${STAMP}"
bash "${DIR}/scripts/autoevolve.sh" "${STAMP}"

echo "subproject run done: ${DIR}"
echo "reports: ${DIR}/reports"
