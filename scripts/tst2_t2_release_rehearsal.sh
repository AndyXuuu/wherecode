#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_URL="http://127.0.0.1:8000"
ACTION_URL="http://127.0.0.1:8100"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
REPORT_DIR="${TST2_T2_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
LATEST_REPORT_PATH="${TST2_T2_LATEST_REPORT_PATH:-${REPORT_DIR}/latest_tst2_t2_release_rehearsal.md}"
LATEST_SUMMARY_PATH="${TST2_T2_LATEST_SUMMARY_PATH:-${REPORT_DIR}/latest_tst2_t2_release_rehearsal.json}"
REQUIRE_ROLLBACK="${TST2_T2_REQUIRE_ROLLBACK:-false}"
STRICT_MODE=false
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_t2_release_rehearsal.sh [control_url] [action_url] [--strict] [--dry-run]

Options:
  --strict    require rollback drill success and checkpoint guard pass
  --dry-run   print planned actions only

Env:
  TST2_T2_REQUIRE_ROLLBACK=true|false      default: false (auto true in --strict)
EOF
}

is_true() {
  local normalized
  normalized="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "${normalized}" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

POSITIONALS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT_MODE=true
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      POSITIONALS+=("$1")
      ;;
  esac
  shift
done
if [[ ${#POSITIONALS[@]} -gt 0 ]]; then
  set -- "${POSITIONALS[@]}"
else
  set --
fi

if [[ $# -ge 1 ]]; then
  CONTROL_URL="$1"
fi
if [[ $# -ge 2 ]]; then
  ACTION_URL="$2"
fi

if [[ "${STRICT_MODE}" == "true" ]]; then
  REQUIRE_ROLLBACK=true
fi

mkdir -p "${REPORT_DIR}"
stamp="$(date -u +"%Y%m%dT%H%M%SZ")"
report_path="${REPORT_DIR}/${stamp}-tst2-t2-release-rehearsal.md"
ci_log="${REPORT_DIR}/${stamp}-tst2-t2-ci-rehearsal.log"
rollback_log="${REPORT_DIR}/${stamp}-tst2-t2-rollback-drill.log"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] bash scripts/ci_v3_rehearsal.sh ${CONTROL_URL} ${ACTION_URL}"
  echo "[dry-run] curl -H X-WhereCode-Token ${CONTROL_URL}/metrics/workflows/alert-policy/audits?limit=20"
  echo "[dry-run] bash scripts/v3_metrics_policy_rollback.sh <latest_audit_id> --dry-run"
  echo "[dry-run] bash scripts/stationctl.sh soak-checkpoint"
  echo "[dry-run] write latest report: ${LATEST_REPORT_PATH}"
  echo "[dry-run] write latest summary: ${LATEST_SUMMARY_PATH}"
  exit 0
fi

ci_status="failed"
rollback_status="not_run"
checkpoint_status="failed"
overall_passed=false
latest_audit_id=""
checkpoint_path=""
checkpoint_guard="false"
checkpoint_daemon_running="false"

echo "[1/4] run release rehearsal matrix"
set +e
WHERECODE_TOKEN="${AUTH_TOKEN}" \
bash "${ROOT_DIR}/scripts/ci_v3_rehearsal.sh" "${CONTROL_URL}" "${ACTION_URL}" >"${ci_log}" 2>&1
ci_rc=$?
set -e
tail -n 20 "${ci_log}" || true
if [[ "${ci_rc}" -eq 0 ]]; then
  ci_status="passed"
fi

echo "[2/4] resolve rollback drill target audit"
set +e
audits_json="$(curl -fsS "${CONTROL_URL}/metrics/workflows/alert-policy/audits?limit=20" -H "X-WhereCode-Token: ${AUTH_TOKEN}" 2>/dev/null)"
audits_rc=$?
set -e

if [[ "${audits_rc}" -eq 0 ]]; then
  latest_audit_id="$(
    python3 - "${audits_json}" <<'PY'
from __future__ import annotations

import json
import sys

raw = sys.argv[1]
try:
    payload = json.loads(raw)
except Exception:  # noqa: BLE001
    print("")
    raise SystemExit(0)

if not isinstance(payload, list) or not payload:
    print("")
    raise SystemExit(0)

for item in payload:
    if isinstance(item, dict):
        entry_id = str(item.get("id", "")).strip()
        if entry_id:
            print(entry_id)
            raise SystemExit(0)

print("")
PY
  )"
fi

if [[ -z "${latest_audit_id}" ]]; then
  rollback_status="skipped_no_audit"
  echo "rollback drill skipped: no audit id available"
else
  echo "[3/4] run rollback drill (dry-run) audit_id=${latest_audit_id}"
  set +e
  WHERECODE_CONTROL_URL="${CONTROL_URL}" \
  WHERECODE_TOKEN="${AUTH_TOKEN}" \
  METRICS_POLICY_ROLLBACK_UPDATED_BY="release-manager" \
  METRICS_POLICY_ROLLBACK_REASON="tst2-t2 rollback drill" \
  bash "${ROOT_DIR}/scripts/v3_metrics_policy_rollback.sh" "${latest_audit_id}" --dry-run >"${rollback_log}" 2>&1
  rollback_rc=$?
  set -e
  tail -n 20 "${rollback_log}" || true
  if [[ "${rollback_rc}" -eq 0 ]]; then
    rollback_status="passed"
  else
    rollback_status="failed"
  fi
fi

echo "[4/4] capture soak checkpoint"
set +e
checkpoint_output="$(bash "${ROOT_DIR}/scripts/stationctl.sh" soak-checkpoint 2>&1)"
checkpoint_rc=$?
set -e
printf '%s\n' "${checkpoint_output}"

checkpoint_path="$(printf '%s\n' "${checkpoint_output}" | sed -n 's/^checkpoint_written=//p' | tail -n 1)"
checkpoint_guard="$(printf '%s\n' "${checkpoint_output}" | sed -n 's/^guard_passed=//p' | tail -n 1)"
checkpoint_daemon_running="$(printf '%s\n' "${checkpoint_output}" | sed -n 's/^daemon_running=//p' | tail -n 1)"

if [[ "${checkpoint_rc}" -eq 0 ]]; then
  checkpoint_status="passed"
fi

overall_passed=true
if [[ "${ci_status}" != "passed" ]]; then
  overall_passed=false
fi
if is_true "${REQUIRE_ROLLBACK}" && [[ "${rollback_status}" != "passed" ]]; then
  overall_passed=false
fi
if [[ "${STRICT_MODE}" == "true" && "${checkpoint_guard}" != "true" ]]; then
  overall_passed=false
fi

{
  echo "# TST2-T2 release rehearsal report (${stamp:0:8})"
  echo
  echo "## Runtime"
  echo
  echo "- captured_at_utc: \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
  echo "- control_url: \`${CONTROL_URL}\`"
  echo "- action_url: \`${ACTION_URL}\`"
  echo "- strict_mode: \`${STRICT_MODE}\`"
  echo "- require_rollback: \`${REQUIRE_ROLLBACK}\`"
  echo
  echo "## Result"
  echo
  echo "- ci_rehearsal_status: \`${ci_status}\`"
  echo "- rollback_drill_status: \`${rollback_status}\`"
  echo "- rollback_audit_id: \`${latest_audit_id}\`"
  echo "- checkpoint_status: \`${checkpoint_status}\`"
  echo "- checkpoint_guard_passed: \`${checkpoint_guard}\`"
  echo "- checkpoint_daemon_running: \`${checkpoint_daemon_running}\`"
  echo "- checkpoint_report: \`${checkpoint_path}\`"
  echo "- overall_passed: \`${overall_passed}\`"
  echo
  echo "## Logs"
  echo
  echo "- ci_log: \`${ci_log}\`"
  if [[ -f "${rollback_log}" ]]; then
    echo "- rollback_log: \`${rollback_log}\`"
  else
    echo "- rollback_log: \`(not generated)\`"
  fi
} >"${report_path}"

cp "${report_path}" "${LATEST_REPORT_PATH}"

python3 - "${LATEST_SUMMARY_PATH}" "${report_path}" "${ci_status}" "${rollback_status}" "${latest_audit_id}" "${checkpoint_status}" "${checkpoint_guard}" "${checkpoint_daemon_running}" "${checkpoint_path}" "${overall_passed}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

summary_path = Path(sys.argv[1])
payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "report_path": sys.argv[2],
    "ci_rehearsal_status": sys.argv[3],
    "rollback_drill_status": sys.argv[4],
    "rollback_audit_id": sys.argv[5],
    "checkpoint_status": sys.argv[6],
    "checkpoint_guard_passed": sys.argv[7] == "true",
    "checkpoint_daemon_running": sys.argv[8] == "true",
    "checkpoint_report": sys.argv[9],
    "overall_passed": sys.argv[10] == "true",
}
summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

echo "report_written=${report_path}"
echo "latest_report=${LATEST_REPORT_PATH}"
echo "latest_summary=${LATEST_SUMMARY_PATH}"
echo "overall_passed=${overall_passed}"

if [[ "${overall_passed}" != "true" ]]; then
  exit 1
fi
