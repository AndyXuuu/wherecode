#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_URL="${CHECK_ALL_CONTROL_URL:-${WHERECODE_CONTROL_URL:-http://127.0.0.1:8000}}"
TOKEN="${CHECK_ALL_TOKEN:-${WHERECODE_TOKEN:-change-me}}"
REQUESTED_BY="${CHECK_ALL_REQUESTED_BY:-check-all}"
WAIT_TIMEOUT_SECONDS="${CHECK_ALL_WAIT_TIMEOUT_SECONDS:-3600}"
ASYNC_MODE="false"
JSON_OUTPUT="false"
FORCE_LOCAL="${CHECK_ALL_FORCE_LOCAL:-false}"

usage() {
  cat <<'EOF_USAGE'
Usage:
  bash scripts/check_all.sh [scope] [options]

Scopes:
  quick|dev|release|ops|main|all|backend|backend-quick|backend-full|llm-check|frontend|projects

Options:
  --async                     create check run and return immediately
  --timeout <seconds>         wait timeout for sync mode (default: 3600)
  --control-url <url>         control center url
  --token <token>             auth token (X-WhereCode-Token)
  --requested-by <name>       requester label
  --json                      print raw API response
  --local                     force local direct execution (check_all_local.sh)
  -h, --help

Examples:
  bash scripts/check_all.sh quick
  bash scripts/check_all.sh release --async
  bash scripts/check_all.sh main --control-url http://127.0.0.1:8000
EOF_USAGE
}

scope="quick"
scope_set="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --async)
      ASYNC_MODE="true"
      ;;
    --timeout)
      WAIT_TIMEOUT_SECONDS="${2:-}"
      shift
      ;;
    --control-url)
      CONTROL_URL="${2:-}"
      shift
      ;;
    --token)
      TOKEN="${2:-}"
      shift
      ;;
    --requested-by)
      REQUESTED_BY="${2:-}"
      shift
      ;;
    --json)
      JSON_OUTPUT="true"
      ;;
    --local)
      FORCE_LOCAL="true"
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    -* )
      echo "unknown option: $1"
      usage
      exit 1
      ;;
    *)
      if [[ "${scope_set}" == "true" ]]; then
        echo "unexpected argument: $1"
        usage
        exit 1
      fi
      scope="$1"
      scope_set="true"
      ;;
  esac
  shift
done

if [[ "${FORCE_LOCAL}" == "true" ]]; then
  bash "${ROOT_DIR}/scripts/check_all_local.sh" "${scope}"
  exit $?
fi

wait_seconds="${WAIT_TIMEOUT_SECONDS}"
if [[ "${ASYNC_MODE}" == "true" ]]; then
  wait_seconds="0"
fi

payload="$({
  python3 - "${scope}" "${REQUESTED_BY}" "${wait_seconds}" <<'PY'
import json
import sys

scope = sys.argv[1].strip()
requested_by = sys.argv[2].strip() or "check-all"
wait_seconds = int(sys.argv[3])
print(
    json.dumps(
        {
            "scope": scope,
            "requested_by": requested_by,
            "wait_seconds": wait_seconds,
        },
        ensure_ascii=False,
    )
)
PY
})"

response="$(curl -fsS -X POST "${CONTROL_URL}/ops/checks/runs" \
  -H "Content-Type: application/json" \
  -H "X-WhereCode-Token: ${TOKEN}" \
  -d "${payload}")"

if [[ "${JSON_OUTPUT}" == "true" ]]; then
  printf '%s\n' "${response}"
fi

parsed="$({
  python3 - <<'PY' "${response}"
import json
import sys

payload = json.loads(sys.argv[1])
print(str(payload.get("run_id") or ""))
print(str(payload.get("scope") or ""))
print(str(payload.get("status") or ""))
print(str(payload.get("message") or ""))
print(str(payload.get("log_path") or ""))
print(str(payload.get("report_path") or ""))
print(str(payload.get("started_at") or ""))
print(str(payload.get("finished_at") or ""))
PY
})"

run_id="$(echo "${parsed}" | sed -n '1p')"
run_scope="$(echo "${parsed}" | sed -n '2p')"
run_status="$(echo "${parsed}" | sed -n '3p')"
run_message="$(echo "${parsed}" | sed -n '4p')"
run_log_path="$(echo "${parsed}" | sed -n '5p')"
run_report_path="$(echo "${parsed}" | sed -n '6p')"
run_started_at="$(echo "${parsed}" | sed -n '7p')"
run_finished_at="$(echo "${parsed}" | sed -n '8p')"

echo "check_run_id=${run_id}"
echo "scope=${run_scope}"
echo "status=${run_status}"
[[ -n "${run_message}" ]] && echo "message=${run_message}"
[[ -n "${run_started_at}" ]] && echo "started_at=${run_started_at}"
[[ -n "${run_finished_at}" ]] && echo "finished_at=${run_finished_at}"
[[ -n "${run_log_path}" ]] && echo "log_path=${run_log_path}"
[[ -n "${run_report_path}" ]] && echo "report_path=${run_report_path}"

if [[ "${ASYNC_MODE}" == "true" ]]; then
  exit 0
fi

if [[ "${run_status}" != "success" ]]; then
  exit 1
fi
