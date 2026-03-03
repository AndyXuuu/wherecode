from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)


def test_v3_workflow_api_parallel_then_join_flow() -> None:
    run_response = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_v3", "requested_by": "andy"},
    )
    assert run_response.status_code == 201
    run = run_response.json()
    run_id = run["id"]
    assert run_id.startswith("wfr_")
    assert run["status"] == "running"

    first = client.post(
        f"/v3/workflows/runs/{run_id}/workitems",
        json={"role": "module-dev", "module_key": "auth"},
    ).json()
    second = client.post(
        f"/v3/workflows/runs/{run_id}/workitems",
        json={"role": "module-dev", "module_key": "billing"},
    ).json()
    join_resp = client.post(
        f"/v3/workflows/runs/{run_id}/workitems",
        json={
            "role": "qa-test",
            "module_key": "integration",
            "depends_on": [first["id"], second["id"]],
        },
    )
    assert join_resp.status_code == 201
    join = join_resp.json()

    tick_one = client.post(f"/v3/workflows/runs/{run_id}/tick")
    assert tick_one.status_code == 200
    ready_ids = {item["id"] for item in tick_one.json()}
    assert ready_ids == {first["id"], second["id"]}

    start_first = client.post(f"/v3/workflows/workitems/{first['id']}/start")
    assert start_first.status_code == 200
    start_second = client.post(f"/v3/workflows/workitems/{second['id']}/start")
    assert start_second.status_code == 200

    complete_first = client.post(
        f"/v3/workflows/workitems/{first['id']}/complete",
        json={"success": True},
    )
    assert complete_first.status_code == 200

    tick_two = client.post(f"/v3/workflows/runs/{run_id}/tick")
    assert tick_two.status_code == 200
    assert tick_two.json() == []

    complete_second = client.post(
        f"/v3/workflows/workitems/{second['id']}/complete",
        json={"success": True},
    )
    assert complete_second.status_code == 200

    tick_three = client.post(f"/v3/workflows/runs/{run_id}/tick")
    assert tick_three.status_code == 200
    assert [item["id"] for item in tick_three.json()] == [join["id"]]

    assert client.post(f"/v3/workflows/workitems/{join['id']}/start").status_code == 200
    assert (
        client.post(
            f"/v3/workflows/workitems/{join['id']}/complete",
            json={"success": True},
        ).status_code
        == 200
    )

    run_after = client.get(f"/v3/workflows/runs/{run_id}")
    assert run_after.status_code == 200
    assert run_after.json()["status"] == "succeeded"

    listed = client.get(f"/v3/workflows/runs/{run_id}/workitems")
    assert listed.status_code == 200
    assert len(listed.json()) == 3


def test_v3_workflow_api_rejects_unknown_dependency() -> None:
    run_response = client.post("/v3/workflows/runs", json={"project_id": "proj_v3_dep"})
    run_id = run_response.json()["id"]

    response = client.post(
        f"/v3/workflows/runs/{run_id}/workitems",
        json={"role": "qa-test", "depends_on": ["wi_missing"]},
    )
    assert response.status_code == 422
    assert "dependency workitem not found" in response.json()["detail"]


def test_v3_workflow_api_unknown_run_returns_404() -> None:
    response = client.get("/v3/workflows/runs/wfr_missing")
    assert response.status_code == 404


def test_v3_workflow_start_non_ready_returns_409() -> None:
    run_response = client.post("/v3/workflows/runs", json={"project_id": "proj_v3_status"})
    run_id = run_response.json()["id"]
    workitem = client.post(
        f"/v3/workflows/runs/{run_id}/workitems",
        json={"role": "module-dev"},
    ).json()

    response = client.post(f"/v3/workflows/workitems/{workitem['id']}/start")
    assert response.status_code == 409
