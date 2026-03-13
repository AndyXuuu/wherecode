from pathlib import Path

from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)
HEADERS = {"X-WhereCode-Token": "change-me"}


def test_ops_check_scopes_contains_core_scope() -> None:
    response = client.get("/ops/checks/scopes", headers=HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert "scopes" in payload
    assert "quick" in payload["scopes"]
    assert "main" in payload["scopes"]


def test_ops_check_run_create_and_latest() -> None:
    create = client.post(
        "/ops/checks/runs",
        json={"scope": "quick", "requested_by": "test", "wait_seconds": 300},
        headers=HEADERS,
    )
    assert create.status_code == 201
    payload = create.json()

    assert payload["scope"] == "quick"
    assert payload["status"] == "success"
    assert payload.get("run_id")

    report_path = Path(payload.get("report_path", ""))
    assert report_path.exists()

    latest = client.get("/ops/checks/latest", params={"scope": "quick"}, headers=HEADERS)
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["run_id"] == payload["run_id"]
    assert latest_payload["status"] in {"queued", "running", "success", "failed"}
