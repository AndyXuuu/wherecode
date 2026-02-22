#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
AUTH_HEADER="X-WhereCode-Token: ${AUTH_TOKEN}"

echo "[1/4] create project"
PROJECT_JSON="$(curl -sS -X POST "${BASE_URL}/projects" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{"name":"smoke-http-async"}')"
PROJECT_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${PROJECT_JSON}")"
echo "project_id=${PROJECT_ID}"

echo "[2/4] create task"
TASK_JSON="$(curl -sS -X POST "${BASE_URL}/projects/${PROJECT_ID}/tasks" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{"title":"smoke-task"}')"
TASK_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${TASK_JSON}")"
echo "task_id=${TASK_ID}"

echo "[3/4] submit command"
COMMAND_ACCEPTED="$(curl -sS -X POST "${BASE_URL}/tasks/${TASK_ID}/commands" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{"text":"run smoke async flow"}')"
COMMAND_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["command_id"])' <<<"${COMMAND_ACCEPTED}")"
echo "command_id=${COMMAND_ID}"

echo "[4/4] poll command status"
for _ in $(seq 1 20); do
  COMMAND_JSON="$(curl -sS "${BASE_URL}/commands/${COMMAND_ID}" -H "${AUTH_HEADER}")"
  STATUS="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"${COMMAND_JSON}")"
  echo "status=${STATUS}"
  if [[ "${STATUS}" == "success" || "${STATUS}" == "failed" ]]; then
    echo "done"
    exit 0
  fi
  sleep 0.2
done

echo "timeout waiting for command completion"
exit 1
