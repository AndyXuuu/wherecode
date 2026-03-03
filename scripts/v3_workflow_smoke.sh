#!/usr/bin/env bash
set -euo pipefail

CONTROL_URL="${1:-http://127.0.0.1:8000}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"

header_auth=("X-WhereCode-Token: ${AUTH_TOKEN}")
header_json=("Content-Type: application/json" "X-WhereCode-Token: ${AUTH_TOKEN}")

echo "[1/6] create v3 workflow run"
run_payload="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs" \
  -H "${header_json[0]}" \
  -H "${header_json[1]}" \
  -d '{"project_id":"proj_smoke_v3","requested_by":"smoke"}')"
run_id="$(printf '%s' "${run_payload}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
echo "run_id=${run_id}"

echo "[2/6] bootstrap pipeline with discussion module"
curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/bootstrap" \
  -H "${header_json[0]}" \
  -H "${header_json[1]}" \
  -d '{"modules":["needs-discussion"]}' >/dev/null

echo "[3/6] execute until blocked/terminal"
first_execute="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/execute" \
  -H "${header_json[0]}" \
  -H "${header_json[1]}" \
  -d '{"max_loops":40}')"
first_status="$(printf '%s' "${first_execute}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_status"])')"
echo "first_status=${first_status}"

if [[ "${first_status}" == "blocked" ]]; then
  echo "[4/6] resolve discussion and resume"
  discussion_workitem_id="$(printf '%s' "${first_execute}" | python3 -c 'import json,sys; p=json.load(sys.stdin); ids=p.get("waiting_discussion_workitem_ids", []); print(ids[0] if ids else "")')"
  if [[ -z "${discussion_workitem_id}" ]]; then
    echo "blocked but no waiting_discussion_workitem_ids"
    exit 1
  fi

  curl -fsS -X POST "${CONTROL_URL}/v3/workflows/workitems/${discussion_workitem_id}/discussion/resolve" \
    -H "${header_json[0]}" \
    -H "${header_json[1]}" \
    -d '{"decision":"use option-a","resolved_by":"chief-architect"}' >/dev/null
fi

echo "[5/6] execute again (and approve if needed)"
second_execute="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/execute" \
  -H "${header_json[0]}" \
  -H "${header_json[1]}" \
  -d '{"max_loops":80}')"
second_status="$(printf '%s' "${second_execute}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_status"])')"

if [[ "${second_status}" == "waiting_approval" ]]; then
  approval_workitem_id="$(printf '%s' "${second_execute}" | python3 -c 'import json,sys; p=json.load(sys.stdin); ids=p.get("waiting_approval_workitem_ids", []); print(ids[0] if ids else "")')"
  if [[ -z "${approval_workitem_id}" ]]; then
    echo "waiting_approval but no waiting_approval_workitem_ids"
    exit 1
  fi
  curl -fsS -X POST "${CONTROL_URL}/v3/workflows/workitems/${approval_workitem_id}/approve" \
    -H "${header_json[0]}" \
    -H "${header_json[1]}" \
    -d '{"approved_by":"smoke-owner"}' >/dev/null
  second_execute="$(curl -fsS -X POST "${CONTROL_URL}/v3/workflows/runs/${run_id}/execute" \
    -H "${header_json[0]}" \
    -H "${header_json[1]}" \
    -d '{"max_loops":80}')"
  second_status="$(printf '%s' "${second_execute}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_status"])')"
fi

echo "[6/6] verify final status and artifacts"
if [[ "${second_status}" != "succeeded" ]]; then
  echo "v3 workflow smoke failed: final status=${second_status}"
  printf '%s\n' "${second_execute}"
  exit 1
fi

artifacts="$(curl -fsS "${CONTROL_URL}/v3/workflows/runs/${run_id}/artifacts" \
  -H "${header_auth[0]}")"
artifact_count="$(printf '%s' "${artifacts}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
if [[ "${artifact_count}" -lt 1 ]]; then
  echo "v3 workflow smoke failed: no artifacts generated"
  exit 1
fi

echo "v3 workflow smoke passed"
