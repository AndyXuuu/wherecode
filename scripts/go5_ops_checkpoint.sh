#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="${2:-$(date -u +%Y%m%dT%H%M%SZ)}"
PROFILE="${1:-quick}"
REPORT_DIR="${GO5_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
SUMMARY_FILE="${3:-${REPORT_DIR}/${STAMP}-go5-ops-checkpoint.json}"
STRICT_MODE="${GO5_STRICT_MODE:-false}"
ENFORCE_PROVIDER_READY="${GO5_ENFORCE_PROVIDER_READY:-false}"
CONTROL_URL="${WHERECODE_CONTROL_URL:-http://127.0.0.1:8000}"
ACTION_URL="${WHERECODE_ACTION_URL:-http://127.0.0.1:8100}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/go5_ops_checkpoint.sh [quick|full] [stamp] [summary_file]

Profiles:
  quick   secret working-tree + provider probe
  full    quick + secret all-history + release check + recovery drill

Env:
  GO5_STRICT_MODE=true               fail script when checkpoint_passed=false
  GO5_ENFORCE_PROVIDER_READY=true    require provider probe checks to be ready
EOF
}

if [[ "${PROFILE}" == "-h" || "${PROFILE}" == "--help" || "${PROFILE}" == "help" ]]; then
  usage
  exit 0
fi

if [[ "${PROFILE}" != "quick" && "${PROFILE}" != "full" ]]; then
  echo "unknown profile: ${PROFILE}"
  usage
  exit 2
fi

mkdir -p "${REPORT_DIR}"

step_secret_working_tree_ec=0
step_secret_all_history_ec=0
step_provider_probe_ec=0
step_release_ec=0
step_recovery_ec=0

run_and_log() {
  local step_name="$1"
  shift
  local log_file="${REPORT_DIR}/${STAMP}-go5-${step_name}.log"
  local ec=0
  set +e
  "$@" >"${log_file}" 2>&1
  ec=$?
  set -e
  echo "[${step_name}] exit_code=${ec} log=${log_file}"
  return "${ec}"
}

echo "[go5] profile=${PROFILE} stamp=${STAMP}"
echo "[go5] reports=${REPORT_DIR}"

if run_and_log "secret-working-tree" bash "${ROOT_DIR}/scripts/check_secrets.sh" --working-tree; then
  step_secret_working_tree_ec=0
else
  step_secret_working_tree_ec=$?
fi

provider_report="${REPORT_DIR}/${STAMP}-go5-provider-probe.json"
if run_and_log "provider-probe" bash "${ROOT_DIR}/scripts/go4_provider_probe.sh" "${STAMP}" "${provider_report}"; then
  step_provider_probe_ec=0
else
  step_provider_probe_ec=$?
fi

if [[ "${PROFILE}" == "full" ]]; then
  if run_and_log "secret-all-history" bash "${ROOT_DIR}/scripts/check_secrets.sh" --all-history; then
    step_secret_all_history_ec=0
  else
    step_secret_all_history_ec=$?
  fi

  if run_and_log "release-check" bash "${ROOT_DIR}/scripts/check_all_local.sh" release; then
    step_release_ec=0
  else
    step_release_ec=$?
  fi

  if run_and_log "recovery-drill" bash "${ROOT_DIR}/scripts/v3_recovery_drill.sh" "${CONTROL_URL}" "${ACTION_URL}"; then
    step_recovery_ec=0
  else
    step_recovery_ec=$?
  fi
fi

python3 - <<'PY' \
  "${SUMMARY_FILE}" \
  "${STAMP}" \
  "${PROFILE}" \
  "${ENFORCE_PROVIDER_READY}" \
  "${step_secret_working_tree_ec}" \
  "${step_secret_all_history_ec}" \
  "${step_provider_probe_ec}" \
  "${step_release_ec}" \
  "${step_recovery_ec}" \
  "${provider_report}" \
  "${ROOT_DIR}"
import json
import os
import sys
from pathlib import Path

(
    summary_file,
    stamp,
    profile,
    enforce_provider_ready,
    step_secret_working_tree_ec,
    step_secret_all_history_ec,
    step_provider_probe_ec,
    step_release_ec,
    step_recovery_ec,
    provider_report,
    root_dir,
) = sys.argv[1:]

steps = {
    "secret_working_tree": int(step_secret_working_tree_ec),
    "provider_probe": int(step_provider_probe_ec),
    "secret_all_history": int(step_secret_all_history_ec),
    "release_check": int(step_release_ec),
    "recovery_drill": int(step_recovery_ec),
}

provider_ready = None
provider_probe_path = Path(provider_report)
if provider_probe_path.exists():
    try:
        data = json.loads(provider_probe_path.read_text(encoding="utf-8"))
        checks = data.get("checks", {}) if isinstance(data, dict) else {}
        control_code = str((checks.get("control_health") or {}).get("http_code", ""))
        action_code = str((checks.get("action_health") or {}).get("http_code", ""))
        proxy_code = str((checks.get("proxy_health") or {}).get("http_code", ""))
        runtime_code = str((checks.get("provider_runtime") or {}).get("http_code", ""))
        runtime_ok = runtime_code in {"200", "201"} or runtime_code == "skipped"
        provider_ready = control_code == "200" and action_code == "200" and proxy_code == "200" and runtime_ok
    except Exception:
        provider_ready = False

required_steps = ["secret_working_tree", "provider_probe"]
if profile == "full":
    required_steps.extend(["secret_all_history", "release_check", "recovery_drill"])

checkpoint_passed = all(steps[name] == 0 for name in required_steps)
if enforce_provider_ready.strip().lower() == "true":
    checkpoint_passed = checkpoint_passed and bool(provider_ready)

payload = {
    "stamp": stamp,
    "profile": profile,
    "checkpoint_passed": checkpoint_passed,
    "provider_ready": provider_ready,
    "enforce_provider_ready": enforce_provider_ready.strip().lower() == "true",
    "required_steps": required_steps,
    "step_exit_codes": steps,
    "provider_report": str(provider_probe_path),
}

out_path = Path(summary_file)
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

print(str(out_path))
print(json.dumps(payload, indent=2))
PY

summary_passed="$(
  python3 - <<'PY' "${SUMMARY_FILE}"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("true" if payload.get("checkpoint_passed") else "false")
PY
)"

if [[ "${STRICT_MODE}" == "true" && "${summary_passed}" != "true" ]]; then
  echo "go5 checkpoint failed in strict mode"
  exit 1
fi

echo "go5 checkpoint done: ${SUMMARY_FILE}"
