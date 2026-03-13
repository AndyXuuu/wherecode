from __future__ import annotations

import os

from action_layer.services import AgentProfileLoader, AgentRegistry
from action_layer.services.runtime_execution import ActionRuntimeExecutionService


def _build_service() -> ActionRuntimeExecutionService:
    return ActionRuntimeExecutionService(
        registry=AgentRegistry(),
        profile_loader=AgentProfileLoader(".agents/roles"),
        llm_config=None,
        llm_executor=None,
        llm_init_error="llm not configured",
    )


def test_action_runtime_execution_service_rejects_empty_text() -> None:
    service = _build_service()
    status, payload = service.execute({"text": ""})
    assert int(status) == 422
    assert payload["detail"] == "text must be a non-empty string"


def test_action_runtime_execution_service_resolves_role_to_agent() -> None:
    service = _build_service()
    status, payload = service.execute(
        {
            "text": "hello",
            "role": "module-dev",
        }
    )
    assert int(status) == 503
    assert payload["detail"] == "llm execution is required but not ready"


def test_action_runtime_execution_service_returns_discussion_payload() -> None:
    service = _build_service()
    status, payload = service.execute(
        {
            "text": "role=module-dev; module=needs-discussion; execute stage",
            "role": "module-dev",
        }
    )
    assert int(status) == 200
    assert payload["status"] == "needs_discussion"
    assert payload["discussion"]["fingerprint"] == "needs-discussion-module-dev"
    assert payload["metadata"]["agent_standard"]["protocol"] == "ReAct"
    assert (
        payload["metadata"]["agent_standard"]["trace_schema"]
        == "wherecode://protocols/react_trace/v1"
    )
    assert payload["agent_trace"]["standard"] == "ReAct"
    assert payload["agent_trace"]["loop_state"] == "needs_discussion"


def test_action_runtime_execution_service_mock_response_has_agent_trace() -> None:
    service = _build_service()
    status, payload = service.execute(
        {
            "text": "build module baseline",
        }
    )
    assert int(status) == 503
    assert payload["detail"] == "llm execution is required but not ready"

    previous = os.environ.get("ACTION_LAYER_REQUIRE_LLM")
    os.environ["ACTION_LAYER_REQUIRE_LLM"] = "false"
    try:
        status2, payload2 = service.execute({"text": "run test flow"})
        assert int(status2) == 200
        assert payload2["status"] == "success"
        assert payload2["metadata"]["agent_standard"]["version"] == "1.0"
        assert (
            payload2["metadata"]["agent_standard"]["trace_schema"]
            == "wherecode://protocols/react_trace/v1"
        )
        assert payload2["agent_trace"]["standard"] == "ReAct"
        assert isinstance(payload2["agent_trace"]["steps"], list)
    finally:
        if previous is None:
            os.environ.pop("ACTION_LAYER_REQUIRE_LLM", None)
        else:
            os.environ["ACTION_LAYER_REQUIRE_LLM"] = previous
