from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable

from action_layer.services.llm_executor_exceptions import (
    LLMConfigurationError,
    LLMExecutionError,
)
from action_layer.services.llm_executor_runtime_helpers import (
    default_http_post as _default_http_post,
    extract_message_content as _extract_message_content,
    extract_ollama_content as _extract_ollama_content,
    extract_responses_content as _extract_responses_content,
    format_prompt_payload as _format_prompt_payload,
    parse_llm_text_response as _parse_llm_text_response,
    select_route_target as _select_route_target,
    validate_route_targets as _validate_route_targets,
)


SUPPORTED_STATUSES = {"success", "failed", "needs_discussion"}
SUPPORTED_PROVIDERS = {"openai-compatible", "ollama"}
SUPPORTED_OPENAI_WIRE_APIS = {"chat_completions", "responses"}

DEFAULT_SYSTEM_PROMPT = (
    "You are WhereCode Action Layer executor. "
    "Return strict JSON object only with keys: "
    "status (success|failed|needs_discussion), summary (string), "
    "discussion (optional object with question/options/recommendation/impact/fingerprint), "
    "metadata (optional object), "
    "agent_trace (optional object with standard/version/loop_state/steps/final_decision/truncated)."
)

@dataclass(frozen=True, slots=True)
class LLMProviderConfig:
    target: str
    provider: str
    base_url: str
    model: str
    api_key: str | None
    timeout_seconds: float
    temperature: float
    max_tokens: int
    system_prompt: str
    wire_api: str = "chat_completions"


@dataclass(frozen=True, slots=True)
class LLMRoutingConfig:
    mode: str
    targets: dict[str, LLMProviderConfig]
    default_target: str | None
    role_routes: dict[str, str]
    module_prefix_routes: dict[str, str]

    @classmethod
    def from_env(cls) -> "LLMRoutingConfig":
        mode = os.getenv("ACTION_LAYER_EXECUTION_MODE", "llm").strip().lower() or "llm"
        if mode not in {"mock", "llm"}:
            raise LLMConfigurationError(
                f"invalid ACTION_LAYER_EXECUTION_MODE: {mode} (expected mock|llm)"
            )

        if mode == "mock":
            if os.getenv("ACTION_LAYER_REQUIRE_LLM", "true").strip().lower() == "true":
                raise LLMConfigurationError(
                    "mock mode is disabled when ACTION_LAYER_REQUIRE_LLM=true"
                )
            return cls(
                mode="mock",
                targets={},
                default_target=None,
                role_routes={},
                module_prefix_routes={},
            )

        targets = _load_targets_from_env()
        if not targets:
            raise LLMConfigurationError("no llm targets configured")

        default_target = (
            os.getenv("ACTION_LAYER_LLM_ROUTE_DEFAULT", "default").strip().lower() or "default"
        )
        if default_target not in targets:
            raise LLMConfigurationError(
                f"default llm target not found: {default_target} (configured={sorted(targets.keys())})"
            )

        role_routes = _load_route_mapping("ACTION_LAYER_LLM_ROUTE_BY_ROLE_JSON")
        module_routes = _load_route_mapping("ACTION_LAYER_LLM_ROUTE_BY_MODULE_PREFIX_JSON")
        _validate_route_targets(
            role_routes,
            targets,
            source="ACTION_LAYER_LLM_ROUTE_BY_ROLE_JSON",
        )
        _validate_route_targets(
            module_routes,
            targets,
            source="ACTION_LAYER_LLM_ROUTE_BY_MODULE_PREFIX_JSON",
        )

        return cls(
            mode="llm",
            targets=targets,
            default_target=default_target,
            role_routes=role_routes,
            module_prefix_routes=module_routes,
        )


HttpPostFn = Callable[[str, dict[str, str], dict[str, object], float], dict[str, object]]


def _parse_float(value: object, field_name: str, fallback: float) -> float:
    if value is None:
        return fallback
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise LLMConfigurationError(f"invalid {field_name}: {value}") from exc
    if parsed <= 0:
        raise LLMConfigurationError(f"{field_name} must be > 0")
    return parsed


def _parse_int(value: object, field_name: str, fallback: int) -> int:
    if value is None:
        return fallback
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise LLMConfigurationError(f"invalid {field_name}: {value}") from exc
    if parsed <= 0:
        raise LLMConfigurationError(f"{field_name} must be > 0")
    return parsed


def _normalize_target_name(name: str) -> str:
    normalized = str(name).strip().lower()
    if not normalized:
        raise LLMConfigurationError("llm target name must be non-empty")
    return normalized


def _normalize_openai_wire_api(raw_value: object) -> str:
    value = str(raw_value or "").strip().lower()
    if value in {"chat", "chat_completions", "chat/completions", "chat-completions"}:
        return "chat_completions"
    if value in {"response", "responses"}:
        return "responses"
    if not value:
        return "chat_completions"
    raise LLMConfigurationError(
        f"invalid openai wire_api: {value} "
        f"(supported={sorted(SUPPORTED_OPENAI_WIRE_APIS)})"
    )


def _parse_provider_config(target_name: str, raw: dict[str, object]) -> LLMProviderConfig:
    provider = (
        str(raw.get("provider", "openai-compatible")).strip().lower() or "openai-compatible"
    )
    if provider not in SUPPORTED_PROVIDERS:
        raise LLMConfigurationError(
            f"invalid provider for target={target_name}: {provider} "
            f"(supported={sorted(SUPPORTED_PROVIDERS)})"
        )
    wire_api = (
        _normalize_openai_wire_api(raw.get("wire_api"))
        if provider == "openai-compatible"
        else "chat_completions"
    )

    default_base_url = (
        "http://127.0.0.1:11434" if provider == "ollama" else "https://api.openai.com"
    )
    base_url = str(raw.get("base_url", default_base_url)).strip().rstrip("/")
    if not base_url:
        raise LLMConfigurationError(f"target={target_name} base_url must be non-empty")

    model = str(raw.get("model", "")).strip()
    if not model:
        raise LLMConfigurationError(f"target={target_name} model is required")

    api_key = raw.get("api_key")
    api_key_env = raw.get("api_key_env")
    resolved_api_key: str | None
    if isinstance(api_key_env, str) and api_key_env.strip():
        resolved_api_key = os.getenv(api_key_env.strip())
    elif isinstance(api_key, str):
        resolved_api_key = api_key
    else:
        resolved_api_key = None
    if isinstance(resolved_api_key, str):
        resolved_api_key = resolved_api_key.strip() or None

    timeout_seconds = _parse_float(
        raw.get("timeout_seconds"),
        f"target={target_name}.timeout_seconds",
        30.0,
    )
    temperature = _parse_float(
        raw.get("temperature"),
        f"target={target_name}.temperature",
        0.2,
    )
    max_tokens = _parse_int(
        raw.get("max_tokens"),
        f"target={target_name}.max_tokens",
        800,
    )
    system_prompt = str(raw.get("system_prompt", DEFAULT_SYSTEM_PROMPT)).strip()
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    return LLMProviderConfig(
        target=target_name,
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=resolved_api_key,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        wire_api=wire_api,
    )


def _load_targets_from_env() -> dict[str, LLMProviderConfig]:
    targets_json = os.getenv("ACTION_LAYER_LLM_TARGETS_JSON", "").strip()
    if targets_json:
        try:
            parsed = json.loads(targets_json)
        except json.JSONDecodeError as exc:
            raise LLMConfigurationError(
                f"invalid ACTION_LAYER_LLM_TARGETS_JSON: {exc.msg}"
            ) from exc
        if not isinstance(parsed, dict):
            raise LLMConfigurationError("ACTION_LAYER_LLM_TARGETS_JSON must be an object")

        targets: dict[str, LLMProviderConfig] = {}
        for raw_name, raw_value in parsed.items():
            name = _normalize_target_name(str(raw_name))
            if not isinstance(raw_value, dict):
                raise LLMConfigurationError(
                    f"ACTION_LAYER_LLM_TARGETS_JSON[{name}] must be an object"
                )
            targets[name] = _parse_provider_config(name, raw_value)
        return targets

    provider = os.getenv("ACTION_LAYER_LLM_PROVIDER", "openai-compatible").strip().lower()
    base_url = os.getenv(
        "ACTION_LAYER_LLM_BASE_URL",
        "https://api.openai.com" if provider != "ollama" else "http://127.0.0.1:11434",
    ).strip()
    model = os.getenv("ACTION_LAYER_LLM_MODEL", "").strip()
    if not model:
        raise LLMConfigurationError("ACTION_LAYER_LLM_MODEL is required when mode=llm")

    fallback_raw: dict[str, object] = {
        "provider": provider,
        "wire_api": os.getenv("ACTION_LAYER_LLM_WIRE_API", "chat_completions"),
        "base_url": base_url,
        "model": model,
        "api_key": os.getenv("ACTION_LAYER_LLM_API_KEY"),
        "timeout_seconds": os.getenv("ACTION_LAYER_LLM_TIMEOUT_SECONDS", "120"),
        "temperature": os.getenv("ACTION_LAYER_LLM_TEMPERATURE", "0.2"),
        "max_tokens": os.getenv("ACTION_LAYER_LLM_MAX_TOKENS", "800"),
        "system_prompt": os.getenv("ACTION_LAYER_LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
    }
    return {"default": _parse_provider_config("default", fallback_raw)}


def _load_route_mapping(env_name: str) -> dict[str, str]:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMConfigurationError(f"invalid {env_name}: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise LLMConfigurationError(f"{env_name} must be an object")

    output: dict[str, str] = {}
    for key, value in parsed.items():
        normalized_key = str(key).strip().lower()
        normalized_target = str(value).strip().lower()
        if not normalized_key or not normalized_target:
            raise LLMConfigurationError(f"{env_name} contains empty key/target")
        output[normalized_key] = normalized_target
    return output


class OpenAICompatibleLLMExecutor:
    def __init__(
        self,
        config: LLMProviderConfig,
        http_post: HttpPostFn | None = None,
    ) -> None:
        self._config = config
        self._http_post = http_post or _default_http_post

    @property
    def config(self) -> LLMProviderConfig:
        return self._config

    def execute(self, payload: dict[str, object]) -> dict[str, object]:
        prompt_input = _format_prompt_payload(payload, fallback_agent="coding-agent")
        agent = str(prompt_input["agent"])
        headers = {
            "Content-Type": "application/json",
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        if self._config.wire_api == "responses":
            endpoint = (
                f"{self._config.base_url}/responses"
                if self._config.base_url.endswith("/v1")
                else f"{self._config.base_url}/v1/responses"
            )
            request_payload = {
                "model": self._config.model,
                "input": [
                    {"role": "system", "content": self._config.system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(prompt_input, ensure_ascii=False),
                    },
                ],
                "temperature": self._config.temperature,
                "max_output_tokens": self._config.max_tokens,
            }
        else:
            endpoint = (
                f"{self._config.base_url}/chat/completions"
                if self._config.base_url.endswith("/v1")
                else f"{self._config.base_url}/v1/chat/completions"
            )
            request_payload = {
                "model": self._config.model,
                "messages": [
                    {"role": "system", "content": self._config.system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(prompt_input, ensure_ascii=False),
                    },
                ],
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
            }

        response_payload = self._http_post(
            endpoint,
            headers,
            request_payload,
            self._config.timeout_seconds,
        )
        assistant_text = (
            _extract_responses_content(response_payload)
            if self._config.wire_api == "responses"
            else _extract_message_content(response_payload)
        )
        result = _parse_llm_text_response(
            assistant_text,
            supported_statuses=SUPPORTED_STATUSES,
            provider=self._config.provider,
            model=self._config.model,
            endpoint=endpoint,
            agent=agent,
            route_target=self._config.target,
        )
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["llm_wire_api"] = self._config.wire_api
        result["metadata"] = metadata
        return result


class OllamaLLMExecutor:
    def __init__(
        self,
        config: LLMProviderConfig,
        http_post: HttpPostFn | None = None,
    ) -> None:
        self._config = config
        self._http_post = http_post or _default_http_post

    @property
    def config(self) -> LLMProviderConfig:
        return self._config

    def execute(self, payload: dict[str, object]) -> dict[str, object]:
        prompt_input = _format_prompt_payload(payload, fallback_agent="coding-agent")
        agent = str(prompt_input["agent"])
        request_payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": self._config.system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(prompt_input, ensure_ascii=False),
                },
            ],
            "stream": False,
            "options": {
                "temperature": self._config.temperature,
                "num_predict": self._config.max_tokens,
            },
        }

        endpoint = f"{self._config.base_url}/api/chat"
        response_payload = self._http_post(
            endpoint,
            {"Content-Type": "application/json"},
            request_payload,
            self._config.timeout_seconds,
        )
        assistant_text = _extract_ollama_content(response_payload)
        return _parse_llm_text_response(
            assistant_text,
            supported_statuses=SUPPORTED_STATUSES,
            provider=self._config.provider,
            model=self._config.model,
            endpoint=endpoint,
            agent=agent,
            route_target=self._config.target,
        )


class RoutedLLMExecutor:
    def __init__(
        self,
        config: LLMRoutingConfig,
        http_post: HttpPostFn | None = None,
    ) -> None:
        if config.mode != "llm":
            raise LLMConfigurationError("RoutedLLMExecutor requires mode=llm")
        self._config = config
        self._executors: dict[str, OpenAICompatibleLLMExecutor | OllamaLLMExecutor] = {}
        for target_name, provider_config in config.targets.items():
            if provider_config.provider == "openai-compatible":
                self._executors[target_name] = OpenAICompatibleLLMExecutor(
                    provider_config,
                    http_post=http_post,
                )
                continue
            if provider_config.provider == "ollama":
                self._executors[target_name] = OllamaLLMExecutor(
                    provider_config,
                    http_post=http_post,
                )
                continue
            raise LLMConfigurationError(
                f"unsupported provider in runtime: {provider_config.provider}"
            )

    @property
    def config(self) -> LLMRoutingConfig:
        return self._config

    def provider_label(self) -> str:
        providers = sorted({target.provider for target in self._config.targets.values()})
        if not providers:
            return "unknown"
        if len(providers) == 1:
            return providers[0]
        return "multi"

    def execute(self, payload: dict[str, object]) -> dict[str, object]:
        target_name, route_reason = self._select_target(payload)
        executor = self._executors.get(target_name)
        if executor is None:
            raise LLMExecutionError(f"target executor not found: {target_name}")

        result = executor.execute(payload)
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["llm_route_reason"] = route_reason
        result["metadata"] = metadata
        return result

    def _select_target(self, payload: dict[str, object]) -> tuple[str, str]:
        return _select_route_target(
            payload,
            module_prefix_routes=self._config.module_prefix_routes,
            role_routes=self._config.role_routes,
            default_target=self._config.default_target,
        )
