from fastapi.testclient import TestClient

import control_center.main as main_module
from control_center.main import app


client = TestClient(app)


def test_healthz_whitelisted_without_token(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")

    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_route_requires_token(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")

    missing = client.post("/projects", json={"name": "no-token"})
    assert missing.status_code == 401
    assert missing.json()["detail"] == "unauthorized"

    wrong = client.post(
        "/projects",
        json={"name": "wrong-token"},
        headers={"X-WhereCode-Token": "bad-token"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "unauthorized"


def test_protected_route_accepts_token_header(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")

    response = client.post(
        "/projects",
        json={"name": "x-token"},
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "x-token"


def test_protected_route_accepts_bearer_header(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")

    response = client.post(
        "/projects",
        json={"name": "bearer-token"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "bearer-token"
