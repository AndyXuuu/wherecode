from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)


def test_openapi_contains_expected_core_paths() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    assert spec["info"]["title"] == "WhereCode Control Center"

    paths = spec["paths"]
    required_path_methods = {
        "/healthz": {"get"},
        "/action-layer/health": {"get"},
        "/action-layer/execute": {"post"},
        "/projects": {"get", "post"},
        "/projects/{project_id}/tasks": {"get", "post"},
        "/tasks/{task_id}": {"get"},
        "/tasks/{task_id}/commands": {"get", "post"},
        "/commands/{command_id}": {"get"},
        "/commands/{command_id}/approve": {"post"},
        "/projects/{project_id}/snapshot": {"get"},
    }

    for path, methods in required_path_methods.items():
        assert path in paths
        assert methods.issubset(set(paths[path].keys()))


def test_openapi_command_acceptance_response_contract() -> None:
    spec = client.get("/openapi.json").json()

    command_post = spec["paths"]["/tasks/{task_id}/commands"]["post"]
    responses = command_post["responses"]
    assert "202" in responses

    content = responses["202"]["content"]["application/json"]["schema"]
    assert content["$ref"] == "#/components/schemas/CommandAcceptedResponse"

    schema = spec["components"]["schemas"]["CommandAcceptedResponse"]
    required_fields = set(schema["required"])
    assert {"command_id", "task_id", "project_id", "status", "poll_url"}.issubset(required_fields)


def test_openapi_validation_schema_contract() -> None:
    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]

    create_command = schemas["CreateCommandRequest"]
    create_command_props = create_command["properties"]
    assert "text" in create_command_props
    assert "requires_approval" in create_command_props
    assert create_command_props["requires_approval"].get("default") is False

    approve_command = schemas["ApproveCommandRequest"]
    assert "approved_by" in approve_command["properties"]
    assert "approved_by" in approve_command["required"]
