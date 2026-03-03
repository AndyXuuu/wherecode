#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_ID="${1:-}"
POLICY_PATH="${WHERECODE_METRICS_ALERT_POLICY_FILE:-${ROOT_DIR}/control_center/metrics_alert_policy.json}"
AUDIT_PATH="${WHERECODE_METRICS_ALERT_AUDIT_FILE:-${ROOT_DIR}/.wherecode/metrics_alert_policy_audit.jsonl}"
CONTROL_URL="${WHERECODE_CONTROL_URL:-http://127.0.0.1:8000}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
UPDATED_BY="${METRICS_POLICY_ROLLBACK_UPDATED_BY:-ops-admin}"
ROLE_HEADER="${METRICS_POLICY_ROLLBACK_ROLE:-${UPDATED_BY}}"
REASON_NOTE="${METRICS_POLICY_ROLLBACK_REASON:-manual rollback}"
IDEMPOTENCY_KEY="${METRICS_POLICY_ROLLBACK_IDEMPOTENCY_KEY:-}"
APPROVAL_ID="${METRICS_POLICY_ROLLBACK_APPROVAL_ID:-}"
DRY_RUN=false
LOCAL_FILE_MODE=false

if [[ -z "${AUDIT_ID}" ]]; then
  echo "usage: bash scripts/v3_metrics_policy_rollback.sh <audit_id> [--dry-run] [--local-file-mode]"
  exit 1
fi

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      ;;
    --local-file-mode)
      LOCAL_FILE_MODE=true
      ;;
    *)
      echo "unknown option: $1"
      exit 1
      ;;
  esac
  shift
done

if [[ "${LOCAL_FILE_MODE}" != "true" ]]; then
  payload="$(python3 - "${AUDIT_ID}" "${UPDATED_BY}" "${REASON_NOTE}" "${DRY_RUN}" "${IDEMPOTENCY_KEY}" "${APPROVAL_ID}" <<'PY'
import json
import sys

audit_id = sys.argv[1]
updated_by = sys.argv[2]
reason_note = sys.argv[3]
dry_run = sys.argv[4].lower() == "true"
idempotency_key = sys.argv[5].strip()
approval_id = sys.argv[6].strip()

body = {
    "audit_id": audit_id,
    "updated_by": updated_by,
    "reason": reason_note,
    "dry_run": dry_run,
}
if idempotency_key:
    body["idempotency_key"] = idempotency_key
if approval_id:
    body["approval_id"] = approval_id

print(
    json.dumps(body, ensure_ascii=False)
)
PY
)"
  curl -fsS -X POST "${CONTROL_URL}/metrics/workflows/alert-policy/rollback" \
    -H "Content-Type: application/json" \
    -H "X-WhereCode-Token: ${AUTH_TOKEN}" \
    -H "X-WhereCode-Role: ${ROLE_HEADER}" \
    -d "${payload}"
  echo
  exit 0
fi

python3 - "${AUDIT_ID}" "${POLICY_PATH}" "${AUDIT_PATH}" "${UPDATED_BY}" "${REASON_NOTE}" "${DRY_RUN}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

audit_id = sys.argv[1]
policy_path = Path(sys.argv[2])
audit_path = Path(sys.argv[3])
updated_by = sys.argv[4].strip()
reason_note = sys.argv[5].strip()
dry_run = sys.argv[6].lower() == "true"

if not audit_path.exists():
    raise SystemExit(f"audit file not found: {audit_path}")
if not updated_by:
    raise SystemExit("METRICS_POLICY_ROLLBACK_UPDATED_BY must be non-empty")

target: dict[str, object] | None = None
for line in audit_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        continue
    if not isinstance(payload, dict):
        continue
    if str(payload.get("id", "")).strip() == audit_id:
        target = payload

if target is None:
    raise SystemExit(f"audit id not found: {audit_id}")

policy = target.get("policy")
if not isinstance(policy, dict):
    raise SystemExit(f"audit id has no policy payload: {audit_id}")

normalized_policy: dict[str, int] = {}
for key, value in policy.items():
    if isinstance(key, str) and isinstance(value, (int, float)):
        normalized_policy[key] = int(value)

if not normalized_policy:
    raise SystemExit(f"audit id has empty numeric policy payload: {audit_id}")

print(f"rollback target audit: {audit_id}")
print(json.dumps(normalized_policy, ensure_ascii=False, indent=2))

if dry_run:
    print("dry-run: no file changes applied")
    raise SystemExit(0)

policy_path.parent.mkdir(parents=True, exist_ok=True)
policy_path.write_text(
    json.dumps(normalized_policy, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
entry = {
    "id": f"map_{uuid4().hex[:12]}",
    "updated_at": timestamp,
    "updated_by": updated_by.lower(),
    "reason": f"rollback_to:{audit_id}; note:{reason_note}",
    "rollback_from_audit_id": audit_id,
    "policy": normalized_policy,
}
audit_path.parent.mkdir(parents=True, exist_ok=True)
with audit_path.open("a", encoding="utf-8") as file:
    file.write(json.dumps(entry, ensure_ascii=False) + "\n")

print(f"rollback applied: policy={policy_path}")
print(f"audit appended: {audit_path}")
PY
