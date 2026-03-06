#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_FILE="${2:-${ROOT_DIR}/docs/ops_reports/${STAMP}-go4-provider-probe.json}"
CONTROL_URL="${WHERECODE_CONTROL_URL:-http://127.0.0.1:8000}"
ACTION_URL="${WHERECODE_ACTION_URL:-http://127.0.0.1:8100}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
CODEX_HOME_DIR="${CODEX_HOME:-${HOME}/.codex}"
CODEX_CONFIG_PATH="${ACTION_LAYER_CODEX_CONFIG_PATH:-${CODEX_HOME_DIR}/config.toml}"
CODEX_AUTH_PATH="${ACTION_LAYER_CODEX_AUTH_PATH:-${CODEX_HOME_DIR}/auth.json}"

load_codex_defaults() {
  local codex_exports
  codex_exports="$(
    python3 - "${CODEX_CONFIG_PATH}" "${CODEX_AUTH_PATH}" <<'PY'
import json
import shlex
import sys
import tomllib
from pathlib import Path

config_path = Path(sys.argv[1])
auth_path = Path(sys.argv[2])
config = {}
provider_cfg = {}
provider_name = ""
base_url = ""
model = ""
wire_api = ""
api_key = ""
provider = "openai-compatible"

if config_path.exists():
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        config = {}
if isinstance(config, dict):
    provider_name = str(config.get("model_provider", "")).strip()
    model = str(config.get("model", "")).strip()
    providers = config.get("model_providers")
    if isinstance(providers, dict) and provider_name:
        raw_provider = providers.get(provider_name)
        if isinstance(raw_provider, dict):
            provider_cfg = raw_provider
    base_url = str(provider_cfg.get("base_url", "")).strip()
    wire_api = str(provider_cfg.get("wire_api", "")).strip()

provider_hint = provider_name.lower()
base_hint = base_url.lower()
if provider_hint == "ollama" or "127.0.0.1:11434" in base_hint or "localhost:11434" in base_hint:
    provider = "ollama"

if auth_path.exists():
    try:
        auth = json.loads(auth_path.read_text(encoding="utf-8"))
    except Exception:
        auth = {}
    if isinstance(auth, dict):
        raw_key = auth.get("OPENAI_API_KEY")
        if isinstance(raw_key, str):
            api_key = raw_key.strip()

exports = {
    "CODEX_DEFAULT_BASE_URL": base_url,
    "CODEX_DEFAULT_MODEL": model,
    "CODEX_DEFAULT_WIRE_API": wire_api,
    "CODEX_DEFAULT_PROVIDER": provider,
    "CODEX_DEFAULT_API_KEY": api_key,
}
for key, value in exports.items():
    if isinstance(value, str) and value.strip():
        print(f"export {key}={shlex.quote(value.strip())}")
PY
  )"
  if [[ -n "${codex_exports}" ]]; then
    eval "${codex_exports}"
  fi
}

load_codex_defaults

BASE_URL="${ACTION_LAYER_LLM_BASE_URL:-${CODEX_DEFAULT_BASE_URL:-https://api.openai.com}}"
MODEL="${ACTION_LAYER_LLM_MODEL:-${CODEX_DEFAULT_MODEL:-}}"
WIRE_API_RAW="${ACTION_LAYER_LLM_WIRE_API:-${CODEX_DEFAULT_WIRE_API:-chat_completions}}"
WIRE_API="$(printf "%s" "${WIRE_API_RAW}" | tr '[:upper:]' '[:lower:]')"
LLM_PROVIDER="${ACTION_LAYER_LLM_PROVIDER:-${CODEX_DEFAULT_PROVIDER:-openai-compatible}}"
PROBE_USER_AGENT="${ACTION_LAYER_LLM_USER_AGENT:-wherecode-action-layer/0.1}"

case "${WIRE_API}" in
  response|responses)
    WIRE_API="responses"
    ;;
  chat|chat_completions|chat/completions|chat-completions)
    WIRE_API="chat_completions"
    ;;
  *)
    WIRE_API="chat_completions"
    ;;
esac

API_KEY_SOURCE="none"
if [[ -n "${ACTION_LAYER_LLM_API_KEY:-}" ]]; then
  API_KEY="${ACTION_LAYER_LLM_API_KEY:-}"
  API_KEY_SOURCE="env:ACTION_LAYER_LLM_API_KEY"
elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
  API_KEY="${OPENAI_API_KEY}"
  API_KEY_SOURCE="env:OPENAI_API_KEY"
else
  API_KEY="${CODEX_DEFAULT_API_KEY:-}"
  if [[ -n "${API_KEY}" ]]; then
    API_KEY_SOURCE="codex_auth"
  fi
fi

mkdir -p "$(dirname "${OUT_FILE}")"

set +e
control_code="$(curl -sS -o /dev/null -w "%{http_code}" "${CONTROL_URL}/healthz")"
control_ec=$?

action_code="$(curl -sS -o /dev/null -w "%{http_code}" "${ACTION_URL}/healthz")"
action_ec=$?

proxy_code="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-WhereCode-Token: ${AUTH_TOKEN}" \
  "${CONTROL_URL}/action-layer/health")"
proxy_ec=$?

provider_models_code=""
provider_models_ec=0
provider_models_snippet=""
if [[ "${LLM_PROVIDER}" == "ollama" ]]; then
  provider_models_ec=0
  provider_models_code="skipped"
  provider_models_snippet="provider=ollama; models endpoint probe skipped"
elif [[ -n "${API_KEY}" ]]; then
  provider_models_payload="$(curl -sS -g -w $'\n%{http_code}' \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -H "User-Agent: ${PROBE_USER_AGENT}" \
    --url "${BASE_URL%/}/v1/models")"
  provider_models_ec=$?
  provider_models_code="$(printf "%s\n" "${provider_models_payload}" | tail -n 1)"
  provider_models_snippet="$(
    python3 - <<'PY' "${provider_models_payload}"
import sys
import re

payload = sys.argv[1]
lines = payload.splitlines()
body = "\n".join(lines[:-1]) if lines else ""
text = body.replace("\n", " ")
text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", text)
text = re.sub(r"Incorrect API key provided:[^\"]+", "Incorrect API key provided: <redacted>", text)
print(text[:240])
PY
  )"
else
  provider_models_ec=1
  provider_models_code="no_api_key"
  provider_models_snippet="API key not found in ACTION_LAYER_LLM_API_KEY / OPENAI_API_KEY / codex auth"
fi

provider_runtime_ec=0
provider_runtime_code=""
provider_runtime_snippet=""
provider_runtime_endpoint=""
if [[ "${LLM_PROVIDER}" == "ollama" ]]; then
  provider_runtime_endpoint="${BASE_URL%/}/api/tags"
  provider_runtime_payload="$(curl -sS -w $'\n%{http_code}' "${provider_runtime_endpoint}")"
  provider_runtime_ec=$?
  provider_runtime_code="$(printf "%s\n" "${provider_runtime_payload}" | tail -n 1)"
  provider_runtime_snippet="$(
    python3 - <<'PY' "${provider_runtime_payload}"
import sys
import re

payload = sys.argv[1]
lines = payload.splitlines()
body = "\n".join(lines[:-1]) if lines else ""
text = body.replace("\n", " ")
text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", text)
print(text[:240])
PY
  )"
elif [[ -z "${MODEL}" ]]; then
  provider_runtime_ec=1
  provider_runtime_code="no_model"
  provider_runtime_snippet="Model not found in ACTION_LAYER_LLM_MODEL / codex config"
elif [[ -z "${API_KEY}" ]]; then
  provider_runtime_ec=1
  provider_runtime_code="no_api_key"
  provider_runtime_snippet="API key not found in ACTION_LAYER_LLM_API_KEY / OPENAI_API_KEY / codex auth"
elif [[ "${WIRE_API}" == "responses" ]]; then
  provider_runtime_endpoint="${BASE_URL%/}/v1/responses"
  runtime_payload_json="$(
    python3 - <<'PY' "${MODEL}"
import json
import sys

model = sys.argv[1]
print(json.dumps({
    "model": model,
    "input": [
        {"role": "system", "content": "Return strict compact JSON."},
        {"role": "user", "content": "return compact json: {\"status\":\"success\",\"summary\":\"probe ok\"}"},
    ],
    "max_output_tokens": 64,
}))
PY
  )"
  provider_runtime_payload="$(curl -sS -g -w $'\n%{http_code}' \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -H "User-Agent: ${PROBE_USER_AGENT}" \
    --data-binary "${runtime_payload_json}" \
    --url "${provider_runtime_endpoint}")"
  provider_runtime_ec=$?
  provider_runtime_code="$(printf "%s\n" "${provider_runtime_payload}" | tail -n 1)"
  provider_runtime_snippet="$(
    python3 - <<'PY' "${provider_runtime_payload}"
import sys
import re

payload = sys.argv[1]
lines = payload.splitlines()
body = "\n".join(lines[:-1]) if lines else ""
text = body.replace("\n", " ")
text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", text)
text = re.sub(r"Incorrect API key provided:[^\"]+", "Incorrect API key provided: <redacted>", text)
print(text[:240])
PY
  )"
else
  provider_runtime_endpoint="${BASE_URL%/}/v1/chat/completions"
  runtime_payload_json="$(
    python3 - <<'PY' "${MODEL}"
import json
import sys

model = sys.argv[1]
print(json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "return compact json: {\"status\":\"success\",\"summary\":\"probe ok\"}"}],
    "temperature": 0,
    "max_tokens": 64,
}))
PY
  )"
  provider_runtime_payload="$(curl -sS -g -w $'\n%{http_code}' \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -H "User-Agent: ${PROBE_USER_AGENT}" \
    --data-binary "${runtime_payload_json}" \
    --url "${provider_runtime_endpoint}")"
  provider_runtime_ec=$?
  provider_runtime_code="$(printf "%s\n" "${provider_runtime_payload}" | tail -n 1)"
  provider_runtime_snippet="$(
    python3 - <<'PY' "${provider_runtime_payload}"
import sys
import re

payload = sys.argv[1]
lines = payload.splitlines()
body = "\n".join(lines[:-1]) if lines else ""
text = body.replace("\n", " ")
text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", text)
text = re.sub(r"Incorrect API key provided:[^\"]+", "Incorrect API key provided: <redacted>", text)
print(text[:240])
PY
  )"
fi
set -e

python3 - <<'PY' \
  "${OUT_FILE}" \
  "${STAMP}" \
  "${CONTROL_URL}" \
  "${ACTION_URL}" \
  "${BASE_URL}" \
  "${MODEL}" \
  "${WIRE_API}" \
  "${LLM_PROVIDER}" \
  "${control_ec}" \
  "${control_code}" \
  "${action_ec}" \
  "${action_code}" \
  "${proxy_ec}" \
  "${proxy_code}" \
  "${provider_models_ec}" \
  "${provider_models_code}" \
  "${provider_models_snippet}" \
  "${provider_runtime_ec}" \
  "${provider_runtime_code}" \
  "${provider_runtime_snippet}" \
  "${provider_runtime_endpoint}" \
  "$( [[ -n "${API_KEY}" ]] && echo true || echo false )" \
  "${API_KEY_SOURCE}"
import json
import sys
from pathlib import Path

(
    out_file,
    stamp,
    control_url,
    action_url,
    base_url,
    model,
    wire_api,
    llm_provider,
    control_ec,
    control_code,
    action_ec,
    action_code,
    proxy_ec,
    proxy_code,
    provider_models_ec,
    provider_models_code,
    provider_models_snippet,
    provider_runtime_ec,
    provider_runtime_code,
    provider_runtime_snippet,
    provider_runtime_endpoint,
    has_api_key,
    api_key_source,
) = sys.argv[1:]

payload = {
    "stamp": stamp,
    "control_url": control_url,
    "action_url": action_url,
    "provider_base_url": base_url,
    "provider_model": model,
    "provider_wire_api": wire_api,
    "provider_type": llm_provider,
    "has_api_key": has_api_key == "true",
    "api_key_source": api_key_source,
    "checks": {
        "control_health": {"exit_code": int(control_ec), "http_code": control_code},
        "action_health": {"exit_code": int(action_ec), "http_code": action_code},
        "proxy_health": {"exit_code": int(proxy_ec), "http_code": proxy_code},
        "provider_models": {
            "exit_code": int(provider_models_ec),
            "http_code": provider_models_code,
            "response_snippet": provider_models_snippet,
        },
        "provider_runtime": {
            "exit_code": int(provider_runtime_ec),
            "http_code": provider_runtime_code,
            "endpoint": provider_runtime_endpoint,
            "response_snippet": provider_runtime_snippet,
        },
    },
}

Path(out_file).write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(out_file)
print(json.dumps(payload, indent=2))
PY
