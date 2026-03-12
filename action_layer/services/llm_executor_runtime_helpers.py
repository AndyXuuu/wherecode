from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from action_layer.services.llm_executor_exceptions import (
    LLMConfigurationError,
    LLMExecutionError,
)


def default_http_post(
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    effective_headers = dict(headers)
    has_user_agent = any(str(key).lower() == "user-agent" for key in effective_headers)
    if not has_user_agent:
        effective_headers["User-Agent"] = os.getenv(
            "ACTION_LAYER_LLM_USER_AGENT",
            "wherecode-action-layer/0.1",
        ).strip() or "wherecode-action-layer/0.1"
    try:
        max_retries = int(os.getenv("ACTION_LAYER_LLM_MAX_RETRIES", "2"))
    except ValueError:
        max_retries = 2
    if max_retries < 0:
        max_retries = 0
    try:
        retry_delay = float(os.getenv("ACTION_LAYER_LLM_RETRY_DELAY_SECONDS", "0.6"))
    except ValueError:
        retry_delay = 0.6
    if retry_delay < 0:
        retry_delay = 0.0

    response_body = ""
    for attempt in range(max_retries + 1):
        request = Request(url=url, data=body_bytes, headers=effective_headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                break
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore").strip()
            can_retry = exc.code >= 500 and attempt < max_retries
            if can_retry:
                time.sleep(retry_delay)
                continue
            raise LLMExecutionError(
                f"llm provider request failed: HTTP {exc.code} {detail}".strip()
            ) from exc
        except URLError as exc:
            can_retry = attempt < max_retries
            if can_retry:
                time.sleep(retry_delay)
                continue
            raise LLMExecutionError(f"llm provider unavailable: {exc}") from exc

    try:
        response_json = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise LLMExecutionError("llm provider returned invalid json response") from exc

    if not isinstance(response_json, dict):
        raise LLMExecutionError("llm provider returned unexpected response object")
    return response_json


def extract_message_content(chat_response: dict[str, object]) -> str:
    choices = chat_response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMExecutionError("llm provider response missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise LLMExecutionError("llm provider response malformed choice")

    message = first.get("message")
    if not isinstance(message, dict):
        raise LLMExecutionError("llm provider response missing message")

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n".join(parts).strip()
    raise LLMExecutionError("llm provider message content is empty")


def extract_responses_content(response_payload: dict[str, object]) -> str:
    output_text = response_payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output_items = response_payload.get("output")
    if not isinstance(output_items, list):
        raise LLMExecutionError("responses api output is missing")
    parts: list[str] = []
    for item in output_items:
        if not isinstance(item, dict):
            continue
        content_items = item.get("content")
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    if parts:
        return "\n".join(parts).strip()

    raise LLMExecutionError("responses api content is empty")


def extract_ollama_content(response_payload: dict[str, object]) -> str:
    message = response_payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    response_text = response_payload.get("response")
    if isinstance(response_text, str) and response_text.strip():
        return response_text.strip()
    raise LLMExecutionError("ollama response content is empty")


def _extract_json_object(text: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _sanitize_discussion(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None

    question = value.get("question")
    if not isinstance(question, str) or not question.strip():
        return None

    raw_options = value.get("options")
    options: list[str] = []
    if isinstance(raw_options, list):
        for item in raw_options:
            if isinstance(item, str) and item.strip():
                options.append(item.strip())
            if len(options) >= 3:
                break

    output: dict[str, object] = {
        "question": question.strip(),
        "options": options,
    }

    recommendation = value.get("recommendation")
    if isinstance(recommendation, str) and recommendation.strip():
        output["recommendation"] = recommendation.strip()
    impact = value.get("impact")
    if isinstance(impact, str) and impact.strip():
        output["impact"] = impact.strip()
    fingerprint = value.get("fingerprint")
    if isinstance(fingerprint, str) and fingerprint.strip():
        output["fingerprint"] = fingerprint.strip()
    return output


def format_prompt_payload(payload: dict[str, object], fallback_agent: str) -> dict[str, object]:
    agent = str(payload.get("agent", "")).strip() or fallback_agent
    return {
        "text": str(payload.get("text", "")).strip(),
        "role": payload.get("role"),
        "module_key": payload.get("module_key"),
        "requested_by": payload.get("requested_by"),
        "task_id": payload.get("task_id"),
        "project_id": payload.get("project_id"),
        "agent": agent,
    }


def parse_llm_text_response(
    assistant_text: str,
    *,
    supported_statuses: set[str],
    provider: str,
    model: str,
    endpoint: str,
    agent: str,
    route_target: str,
) -> dict[str, object]:
    parsed = _extract_json_object(assistant_text)
    metadata: dict[str, object] = {
        "llm_target": route_target,
        "llm_provider": provider,
        "llm_model": model,
        "llm_endpoint": endpoint,
    }

    discussion: dict[str, object] | None = None
    agent_trace: dict[str, object] | None = None
    if isinstance(parsed, dict):
        status = str(parsed.get("status", "success")).strip().lower() or "success"
        if status not in supported_statuses:
            status = "success"

        summary = parsed.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            summary = assistant_text[:280].strip() or "execution completed"

        parsed_metadata = parsed.get("metadata")
        if isinstance(parsed_metadata, dict):
            metadata.update(parsed_metadata)

        discussion = _sanitize_discussion(parsed.get("discussion"))
        raw_trace = parsed.get("agent_trace")
        if isinstance(raw_trace, dict):
            agent_trace = raw_trace
    else:
        status = "success"
        summary = assistant_text[:280].strip() or "execution completed"
        metadata["llm_parse_fallback"] = True

    result: dict[str, object] = {
        "status": status,
        "summary": summary,
        "agent": agent,
        "trace_id": f"act_{uuid4().hex[:12]}",
        "metadata": metadata,
    }
    if discussion is not None and status == "needs_discussion":
        result["discussion"] = discussion
    if agent_trace is not None:
        result["agent_trace"] = agent_trace
    return result


def select_route_target(
    payload: dict[str, object],
    *,
    module_prefix_routes: dict[str, str],
    role_routes: dict[str, str],
    default_target: str | None,
) -> tuple[str, str]:
    module_key = str(payload.get("module_key", "")).strip().lower()
    if module_key:
        for prefix, target in module_prefix_routes.items():
            if module_key.startswith(prefix):
                return target, f"module_prefix:{prefix}"

    role = str(payload.get("role", "")).strip().lower()
    if role and role in role_routes:
        return role_routes[role], f"role:{role}"

    if not default_target:
        raise LLMExecutionError("default llm target is not configured")
    return default_target, "default"


def validate_route_targets(
    routes: dict[str, str],
    targets: dict[str, object],
    *,
    source: str,
) -> None:
    for route_key, target in routes.items():
        if target not in targets:
            raise LLMConfigurationError(
                f"{source} route={route_key} references unknown target={target}"
            )
