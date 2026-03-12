from __future__ import annotations

from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)
HEADERS = {"X-WhereCode-Token": "change-me"}


def test_context_memory_upsert_get_and_list_namespace() -> None:
    shared_upsert = client.put(
        "/context/memory/items",
        json={
            "scope": "shared",
            "key": "preferred_lang",
            "value": "python",
            "updated_by": "chief-architect",
        },
        headers=HEADERS,
    )
    assert shared_upsert.status_code == 200
    assert shared_upsert.json()["namespace_id"] == "shared"

    loaded = client.get(
        "/context/memory/items",
        params={"scope": "shared", "key": "preferred_lang"},
        headers=HEADERS,
    )
    assert loaded.status_code == 200
    assert loaded.json()["value"] == "python"

    list_resp = client.get(
        "/context/memory/namespaces/shared/items",
        params={"prefix": "preferred_"},
        headers=HEADERS,
    )
    assert list_resp.status_code == 200
    keys = {item["key"] for item in list_resp.json()}
    assert "preferred_lang" in keys


def test_context_memory_resolve_overrides_and_delete() -> None:
    client.put(
        "/context/memory/items",
        json={
            "scope": "shared",
            "key": "risk",
            "value": "low",
            "updated_by": "chief-architect",
        },
        headers=HEADERS,
    )
    client.put(
        "/context/memory/items",
        json={
            "scope": "project",
            "project_id": "p_ctx_1",
            "key": "risk",
            "value": "medium",
            "updated_by": "ops",
        },
        headers=HEADERS,
    )
    client.put(
        "/context/memory/items",
        json={
            "scope": "run",
            "project_id": "p_ctx_1",
            "run_id": "run_ctx_1",
            "key": "risk",
            "value": "high",
            "updated_by": "ops",
        },
        headers=HEADERS,
    )

    resolved = client.get(
        "/context/memory/resolve",
        params={"project_id": "p_ctx_1", "run_id": "run_ctx_1"},
        headers=HEADERS,
    )
    assert resolved.status_code == 200
    payload = resolved.json()
    assert payload["values"]["risk"] == "high"
    assert payload["source_namespaces"]["risk"] == "run:run_ctx_1"

    deleted = client.delete(
        "/context/memory/items",
        params={
            "scope": "run",
            "project_id": "p_ctx_1",
            "run_id": "run_ctx_1",
            "key": "risk",
            "deleted_by": "ops",
        },
        headers=HEADERS,
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    missing = client.get(
        "/context/memory/items",
        params={
            "scope": "run",
            "project_id": "p_ctx_1",
            "run_id": "run_ctx_1",
            "key": "risk",
        },
        headers=HEADERS,
    )
    assert missing.status_code == 404
