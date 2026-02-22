#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8100}"

echo "[1/2] action-layer health"
HEALTH_JSON="$(curl -sS "${BASE_URL}/healthz")"
echo "${HEALTH_JSON}"

echo "[2/2] action-layer execute"
EXECUTE_JSON="$(curl -sS -X POST "${BASE_URL}/execute" \
  -H "Content-Type: application/json" \
  -d '{"text":"run smoke execute"}')"
echo "${EXECUTE_JSON}"

echo "done"
