#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

if [[ -x "${VENV_PYTHON}" ]]; then
  PYTHON_BIN="${VENV_PYTHON}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

expand_env_path() {
  local value="$1"
  if [[ "${value}" == "~/"* ]]; then
    echo "${HOME}/${value#~/}"
    return 0
  fi
  echo "${value}"
}

load_env_file() {
  local env_file="$1"
  if [[ -z "${env_file}" ]]; then
    return 0
  fi
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
  fi
}

load_codex_defaults() {
  local use_codex="${ACTION_LAYER_USE_CODEX_CONFIG:-true}"
  case "${use_codex}" in
    false|False|FALSE|0|no|No|NO)
      return 0
      ;;
  esac

  local codex_home codex_config codex_auth codex_exports
  codex_home="${CODEX_HOME:-${HOME}/.codex}"
  codex_config="${ACTION_LAYER_CODEX_CONFIG_PATH:-${codex_home}/config.toml}"
  codex_auth="${ACTION_LAYER_CODEX_AUTH_PATH:-${codex_home}/auth.json}"

  if [[ ! -f "${codex_config}" ]]; then
    return 0
  fi

  codex_exports="$(
    "${PYTHON_BIN}" - "${codex_config}" "${codex_auth}" <<'PY'
import json
import os
import shlex
import sys
import tomllib
from pathlib import Path

config_path = Path(sys.argv[1])
auth_path = Path(sys.argv[2])

try:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

provider_name = str(config.get("model_provider", "")).strip()
providers = config.get("model_providers")
provider_cfg = {}
if isinstance(providers, dict) and provider_name:
    raw_provider = providers.get(provider_name)
    if isinstance(raw_provider, dict):
        provider_cfg = raw_provider

model = str(config.get("model", "")).strip()
base_url = str(provider_cfg.get("base_url", "")).strip()
wire_api = str(provider_cfg.get("wire_api", "")).strip()

provider_hint = provider_name.lower()
base_hint = base_url.lower()
if provider_hint == "ollama" or "127.0.0.1:11434" in base_hint or "localhost:11434" in base_hint:
    llm_provider = "ollama"
else:
    llm_provider = "openai-compatible"

api_key = ""
if auth_path.exists():
    try:
        auth = json.loads(auth_path.read_text(encoding="utf-8"))
        if isinstance(auth, dict):
            raw_key = auth.get("OPENAI_API_KEY")
            if isinstance(raw_key, str):
                api_key = raw_key.strip()
    except Exception:
        pass

existing_openai = str(os.environ.get("OPENAI_API_KEY", "")).strip()
if not api_key and existing_openai:
    api_key = existing_openai

candidates = {
    "ACTION_LAYER_EXECUTION_MODE": "llm",
    "ACTION_LAYER_REQUIRE_LLM": "true",
    "ACTION_LAYER_LLM_PROVIDER": llm_provider,
    "ACTION_LAYER_LLM_BASE_URL": base_url,
    "ACTION_LAYER_LLM_MODEL": model,
    "ACTION_LAYER_LLM_WIRE_API": wire_api,
    "ACTION_LAYER_LLM_API_KEY": api_key,
}

lines = []
for key, value in candidates.items():
    if not isinstance(value, str):
        continue
    normalized = value.strip()
    if not normalized:
        continue
    if str(os.environ.get(key, "")).strip():
        continue
    lines.append(f"export {key}={shlex.quote(normalized)}")

print("\n".join(lines))
PY
  )"

  if [[ -n "${codex_exports}" ]]; then
    eval "${codex_exports}"
  fi
}

load_codex_defaults

SYSTEM_ENV_FILES="${ACTION_LAYER_SYSTEM_ENV_FILES:-/etc/wherecode/action_layer.env:${HOME}/.wherecode/action_layer.env}"
IFS=':' read -r -a system_env_file_list <<< "${SYSTEM_ENV_FILES}"
for raw_path in "${system_env_file_list[@]}"; do
  resolved_path="$(expand_env_path "${raw_path}")"
  load_env_file "${resolved_path}"
done

load_env_file "${SCRIPT_DIR}/.env"

cd "${REPO_ROOT}"
"${PYTHON_BIN}" -m action_layer.runtime
