from __future__ import annotations

import json

import pytest

from action_layer.services.llm_executor import (
    LLMConfigurationError,
    LLMProviderConfig,
    LLMRoutingConfig,
    OllamaLLMExecutor,
    OpenAICompatibleLLMExecutor,
    RoutedLLMExecutor,
)


def test_routing_config_loads_single_target_legacy_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACTION_LAYER_EXECUTION_MODE", "llm")
    monkeypatch.setenv("ACTION_LAYER_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("ACTION_LAYER_LLM_BASE_URL", "https://api.openai.com")
    monkeypatch.setenv("ACTION_LAYER_LLM_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("ACTION_LAYER_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("ACTION_LAYER_LLM_WIRE_API", "responses")
    monkeypatch.delenv("ACTION_LAYER_LLM_TARGETS_JSON", raising=False)

    config = LLMRoutingConfig.from_env()

    assert config.mode == "llm"
    assert config.default_target == "default"
    assert sorted(config.targets.keys()) == ["default"]
    assert config.targets["default"].provider == "openai-compatible"
    assert config.targets["default"].wire_api == "responses"


def test_routing_config_requires_model_when_llm_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACTION_LAYER_EXECUTION_MODE", "llm")
    monkeypatch.delenv("ACTION_LAYER_LLM_MODEL", raising=False)
    monkeypatch.delenv("ACTION_LAYER_LLM_TARGETS_JSON", raising=False)

    with pytest.raises(LLMConfigurationError):
        _ = LLMRoutingConfig.from_env()


def test_routing_config_rejects_mock_when_llm_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACTION_LAYER_EXECUTION_MODE", "mock")
    monkeypatch.setenv("ACTION_LAYER_REQUIRE_LLM", "true")

    with pytest.raises(LLMConfigurationError):
        _ = LLMRoutingConfig.from_env()


def test_routing_config_allows_mock_when_llm_not_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACTION_LAYER_EXECUTION_MODE", "mock")
    monkeypatch.setenv("ACTION_LAYER_REQUIRE_LLM", "false")

    config = LLMRoutingConfig.from_env()
    assert config.mode == "mock"


def test_routing_config_loads_multi_targets_and_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACTION_LAYER_EXECUTION_MODE", "llm")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ACTION_LAYER_LLM_TARGETS_JSON", json.dumps({
        "openai": {
            "provider": "openai-compatible",
            "base_url": "https://api.openai.com",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4.1-mini",
        },
        "local": {
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen2.5:7b",
        },
    }))
    monkeypatch.setenv("ACTION_LAYER_LLM_ROUTE_DEFAULT", "openai")
    monkeypatch.setenv("ACTION_LAYER_LLM_ROUTE_BY_ROLE_JSON", '{"qa-test":"local"}')
    monkeypatch.setenv(
        "ACTION_LAYER_LLM_ROUTE_BY_MODULE_PREFIX_JSON",
        '{"module_x":"openai"}',
    )

    config = LLMRoutingConfig.from_env()

    assert sorted(config.targets.keys()) == ["local", "openai"]
    assert config.role_routes["qa-test"] == "local"
    assert config.module_prefix_routes["module_x"] == "openai"
    assert config.targets["openai"].api_key == "sk-openai"


def test_openai_executor_calls_chat_completions_and_parses_json() -> None:
    captured: dict[str, object] = {}

    def fake_post(url, headers, payload, timeout_seconds):  # noqa: ANN001
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        captured["timeout_seconds"] = timeout_seconds
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status": "needs_discussion",
                                "summary": "need strategy",
                                "discussion": {
                                    "question": "pick one?",
                                    "options": ["a", "b", "c", "d"],
                                },
                            }
                        )
                    }
                }
            ]
        }

    config = LLMProviderConfig(
        target="openai",
        provider="openai-compatible",
        base_url="https://api.openai.com",
        model="gpt-4.1-mini",
        api_key="sk-test",
        timeout_seconds=10.0,
        temperature=0.2,
        max_tokens=256,
        system_prompt="return json",
    )
    executor = OpenAICompatibleLLMExecutor(config, http_post=fake_post)
    result = executor.execute({"text": "implement", "agent": "coding-agent"})

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["timeout_seconds"] == 10.0
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer sk-test"
    assert result["status"] == "needs_discussion"
    assert result["metadata"]["llm_target"] == "openai"
    assert result["metadata"]["llm_wire_api"] == "chat_completions"
    assert result["discussion"]["options"] == ["a", "b", "c"]


def test_openai_executor_parses_agent_trace_contract() -> None:
    def fake_post(url, headers, payload, timeout_seconds):  # noqa: ANN001
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status": "success",
                                "summary": "done",
                                "agent_trace": {
                                    "standard": "ReAct",
                                    "version": "1.0",
                                    "loop_state": "final",
                                    "steps": [
                                        {"phase": "plan", "content": "analyze"},
                                        {"phase": "act", "content": "execute"},
                                    ],
                                    "final_decision": "success",
                                },
                            }
                        )
                    }
                }
            ]
        }

    config = LLMProviderConfig(
        target="openai",
        provider="openai-compatible",
        base_url="https://api.openai.com",
        model="gpt-4.1-mini",
        api_key="sk-test",
        timeout_seconds=10.0,
        temperature=0.2,
        max_tokens=256,
        system_prompt="return json",
    )
    executor = OpenAICompatibleLLMExecutor(config, http_post=fake_post)
    result = executor.execute({"text": "implement", "agent": "coding-agent"})
    assert result["status"] == "success"
    assert result["agent_trace"]["standard"] == "ReAct"
    assert result["agent_trace"]["steps"][0]["phase"] == "plan"


def test_openai_executor_calls_responses_and_parses_output_text() -> None:
    captured: dict[str, object] = {}

    def fake_post(url, headers, payload, timeout_seconds):  # noqa: ANN001
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        captured["timeout_seconds"] = timeout_seconds
        return {
            "output_text": json.dumps(
                {"status": "success", "summary": "responses route ok"}
            )
        }

    config = LLMProviderConfig(
        target="openai",
        provider="openai-compatible",
        base_url="https://api.openai.com",
        model="gpt-4.1-mini",
        api_key="sk-test",
        timeout_seconds=10.0,
        temperature=0.2,
        max_tokens=256,
        system_prompt="return json",
        wire_api="responses",
    )
    executor = OpenAICompatibleLLMExecutor(config, http_post=fake_post)
    result = executor.execute({"text": "implement", "agent": "coding-agent"})

    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert result["status"] == "success"
    assert result["metadata"]["llm_target"] == "openai"
    assert result["metadata"]["llm_wire_api"] == "responses"


def test_ollama_executor_calls_api_chat_and_fallback_text_summary() -> None:
    captured: dict[str, object] = {}

    def fake_post(url, headers, payload, timeout_seconds):  # noqa: ANN001
        captured["url"] = url
        captured["payload"] = payload
        return {"message": {"content": "local model output only text"}}

    config = LLMProviderConfig(
        target="local",
        provider="ollama",
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:7b",
        api_key=None,
        timeout_seconds=15.0,
        temperature=0.1,
        max_tokens=300,
        system_prompt="return json",
    )
    executor = OllamaLLMExecutor(config, http_post=fake_post)
    result = executor.execute({"text": "write tests", "agent": "qa-agent"})

    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert result["status"] == "success"
    assert result["metadata"]["llm_target"] == "local"
    assert result["metadata"]["llm_provider"] == "ollama"
    assert result["metadata"]["llm_parse_fallback"] is True


def test_routed_executor_prefers_module_prefix_then_role() -> None:
    config = LLMRoutingConfig(
        mode="llm",
        targets={
            "openai": LLMProviderConfig(
                target="openai",
                provider="openai-compatible",
                base_url="https://api.openai.com",
                model="gpt-4.1-mini",
                api_key="sk-openai",
                timeout_seconds=20.0,
                temperature=0.2,
                max_tokens=256,
                system_prompt="return json",
            ),
            "local": LLMProviderConfig(
                target="local",
                provider="ollama",
                base_url="http://127.0.0.1:11434",
                model="qwen2.5:7b",
                api_key=None,
                timeout_seconds=20.0,
                temperature=0.2,
                max_tokens=256,
                system_prompt="return json",
            ),
        },
        default_target="openai",
        role_routes={"qa-test": "local"},
        module_prefix_routes={"module_x": "openai"},
    )

    called_urls: list[str] = []

    def fake_post(url, headers, payload, timeout_seconds):  # noqa: ANN001
        called_urls.append(url)
        if url.endswith("/api/chat"):
            return {"message": {"content": json.dumps({"status": "success", "summary": "ok"})}}
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"status": "success", "summary": "ok"})
                    }
                }
            ]
        }

    executor = RoutedLLMExecutor(config, http_post=fake_post)

    module_routed = executor.execute(
        {
            "text": "run module",
            "role": "qa-test",
            "module_key": "module_x/part_a",
            "agent": "qa-agent",
        }
    )
    role_routed = executor.execute(
        {
            "text": "run role",
            "role": "qa-test",
            "module_key": "other_module",
            "agent": "qa-agent",
        }
    )

    assert called_urls[0].endswith("/v1/chat/completions")
    assert called_urls[1].endswith("/api/chat")
    assert module_routed["metadata"]["llm_route_reason"] == "module_prefix:module_x"
    assert role_routed["metadata"]["llm_route_reason"] == "role:qa-test"
