from __future__ import annotations

from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)
HEADERS = {"X-WhereCode-Token": "change-me"}


def test_agent_rules_get_and_reload() -> None:
    get_resp = client.get("/agent-rules", headers=HEADERS)
    assert get_resp.status_code == 200
    payload = get_resp.json()
    assert payload["version"] == "1"
    assert payload["total_roles"] >= 2
    assert "main" in payload["scopes"]
    assert "subproject" in payload["scopes"]

    reload_resp = client.post("/agent-rules/reload", headers=HEADERS)
    assert reload_resp.status_code == 200
    reload_payload = reload_resp.json()
    assert reload_payload["total_roles"] >= 2
