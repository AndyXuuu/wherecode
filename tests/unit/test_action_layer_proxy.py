from fastapi.testclient import TestClient

import control_center.main as main_module
from control_center.main import app
from control_center.models import (
    ActionExecuteResponse,
    ActionLayerHealthResponse,
)
from control_center.services import ActionLayerClientError


client = TestClient(app)


class StubActionLayerOk:
    async def get_health(self) -> ActionLayerHealthResponse:
        return ActionLayerHealthResponse(
            status="ok",
            layer="action",
            transport="http",
        )

    async def execute(self, payload) -> ActionExecuteResponse:
        return ActionExecuteResponse(
            status="success",
            summary=f"executed: {payload.text}",
            agent="coding",
            trace_id="act_stub001",
        )


class StubActionLayerError:
    async def get_health(self) -> ActionLayerHealthResponse:
        raise ActionLayerClientError("action layer unavailable: connect timeout")

    async def execute(self, payload) -> ActionExecuteResponse:
        raise ActionLayerClientError("action layer request failed: HTTP 500")


def test_action_layer_health_proxy_success(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", StubActionLayerOk())
    response = client.get("/action-layer/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "layer": "action",
        "transport": "http",
    }


def test_action_layer_execute_proxy_success(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", StubActionLayerOk())
    response = client.post(
        "/action-layer/execute",
        json={"text": "lint and test", "requested_by": "qa"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["agent"] == "coding"
    assert payload["trace_id"] == "act_stub001"


def test_action_layer_proxy_unavailable_returns_503(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", StubActionLayerError())
    health_resp = client.get("/action-layer/health")
    assert health_resp.status_code == 503
    assert "action layer unavailable" in health_resp.json()["detail"]

    execute_resp = client.post("/action-layer/execute", json={"text": "do something"})
    assert execute_resp.status_code == 503
    assert "action layer request failed" in execute_resp.json()["detail"]


def test_action_layer_execute_validation_422() -> None:
    response = client.post("/action-layer/execute", json={"text": ""})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(item.get("loc", [None])[-1] == "text" for item in detail)
