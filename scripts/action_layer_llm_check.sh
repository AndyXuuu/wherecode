#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8100}"
ROLE="${2:-module-dev}"
MODULE_KEY="${3:-check/default}"
TEXT="${4:-implement llm check and return short summary}"

echo "[1/3] action-layer health"
health_json="$(curl -fsS "${BASE_URL}/healthz")"
echo "${health_json}"

python3 - <<'PY' "${health_json}"
import json
import sys

payload = json.loads(sys.argv[1])
mode = payload.get("mode")
ready = payload.get("llm_ready")
if mode != "llm":
    raise SystemExit(f"health check failed: mode={mode!r}, expected 'llm'")
if ready is not True:
    raise SystemExit(f"health check failed: llm_ready={ready!r}, expected true")
print("health check passed")
PY

echo "[2/3] action-layer execute (llm path)"
request_payload="$(python3 - <<'PY' "${TEXT}" "${ROLE}" "${MODULE_KEY}"
import json
import sys

text = sys.argv[1]
role = sys.argv[2]
module_key = sys.argv[3]
print(json.dumps({
    "text": text,
    "role": role,
    "module_key": module_key,
    "requested_by": "action_layer_llm_check",
}))
PY
)"

execute_json="$(curl -fsS -X POST "${BASE_URL}/execute" \
  -H "Content-Type: application/json" \
  -d "${request_payload}")"
echo "${execute_json}"

python3 - <<'PY' "${execute_json}"
import json
import sys

payload = json.loads(sys.argv[1])
status = payload.get("status")
summary = payload.get("summary")
metadata = payload.get("metadata") or {}
if status not in {"success", "needs_discussion"}:
    raise SystemExit(f"execute failed: status={status!r}")
if not isinstance(summary, str) or not summary.strip():
    raise SystemExit("execute failed: summary is empty")
if metadata.get("execution_mode") != "llm":
    raise SystemExit(f"execute failed: execution_mode={metadata.get('execution_mode')!r}")
if "llm_target" not in metadata:
    raise SystemExit("execute failed: llm_target missing in metadata")
if "llm_provider" not in metadata:
    raise SystemExit("execute failed: llm_provider missing in metadata")
if "llm_route_reason" not in metadata:
    raise SystemExit("execute failed: llm_route_reason missing in metadata")
print("execute check passed")
PY

echo "[3/3] done"
