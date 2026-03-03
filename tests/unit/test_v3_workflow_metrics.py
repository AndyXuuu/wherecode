from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)


def test_workflow_metrics_endpoint_counts_runs_workitems_gates_artifacts() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_metrics", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth"]},
    )
    assert bootstrap.status_code == 200

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert execute.status_code == 200

    metrics = client.get("/metrics/workflows")
    assert metrics.status_code == 200
    payload = metrics.json()

    assert payload["total_runs"] >= 1
    assert payload["total_workitems"] >= 1
    assert payload["total_gate_checks"] >= 1
    assert payload["total_artifacts"] >= 1
    assert payload["run_status_counts"].get("succeeded", 0) >= 1
