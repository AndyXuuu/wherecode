from fastapi.testclient import TestClient

import control_center.main as main_module
from control_center.main import app


client = TestClient(app)


def test_v3_workflow_engine_bootstrap_and_execute_success() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_flow_success", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth", "billing"]},
    )
    assert bootstrap.status_code == 200
    assert len(bootstrap.json()) == 11

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run_status"] == "succeeded"
    assert payload["failed_count"] == 0
    assert payload["remaining_pending_count"] == 0

    run_after = client.get(f"/v3/workflows/runs/{run_id}")
    assert run_after.status_code == 200
    assert run_after.json()["status"] == "succeeded"

    gates = client.get(f"/v3/workflows/runs/{run_id}/gates")
    assert gates.status_code == 200
    assert len(gates.json()) >= 1

    artifacts = client.get(f"/v3/workflows/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    artifact_types = {item["artifact_type"] for item in artifacts.json()}
    assert "acceptance_report" in artifact_types
    assert "release_note" in artifact_types
    assert "rollback_plan" in artifact_types


def test_v3_workflow_engine_execute_failure_path() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_flow_fail", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth", "fail-module"]},
    )
    assert bootstrap.status_code == 200

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run_status"] == "failed"
    assert payload["failed_count"] >= 1


def test_v3_workflow_engine_rejects_duplicate_bootstrap() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_dup", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    first = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth"]},
    )
    assert first.status_code == 200

    second = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["billing"]},
    )
    assert second.status_code == 422


def test_v3_workflow_engine_gate_reflow_success_path() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_gate_reflow", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["doc-reflow-once"]},
    )
    assert bootstrap.status_code == 200

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 50},
    )
    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run_status"] == "succeeded"

    gates = client.get(f"/v3/workflows/runs/{run_id}/gates")
    assert gates.status_code == 200
    gate_statuses = {item["status"] for item in gates.json()}
    assert "failed" in gate_statuses
    assert "passed" in gate_statuses


def test_v3_workflow_engine_discussion_flow_resume() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_discussion", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["needs-discussion"]},
    )
    assert bootstrap.status_code == 200

    first_execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert first_execute.status_code == 200
    first_payload = first_execute.json()
    assert first_payload["run_status"] == "blocked"
    assert first_payload["waiting_discussion_count"] >= 1
    assert len(first_payload["waiting_discussion_workitem_ids"]) >= 1

    target_workitem_id = first_payload["waiting_discussion_workitem_ids"][0]
    discussions = client.get(f"/v3/workflows/workitems/{target_workitem_id}/discussions")
    assert discussions.status_code == 200
    discussion_list = discussions.json()
    assert len(discussion_list) >= 1
    assert discussion_list[-1]["status"] == "open"

    resolve = client.post(
        f"/v3/workflows/workitems/{target_workitem_id}/discussion/resolve",
        json={"decision": "use option-a", "resolved_by": "chief-architect"},
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"

    second_execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert second_execute.status_code == 200
    second_payload = second_execute.json()
    assert second_payload["run_status"] == "succeeded"


def test_v3_workflow_engine_release_approval_switch() -> None:
    main_module.workflow_engine._release_requires_approval = True
    try:
        run = client.post(
            "/v3/workflows/runs",
            json={"project_id": "proj_release_approval", "requested_by": "andy"},
        ).json()
        run_id = run["id"]

        bootstrap = client.post(
            f"/v3/workflows/runs/{run_id}/bootstrap",
            json={"modules": ["auth"]},
        )
        assert bootstrap.status_code == 200

        first_execute = client.post(
            f"/v3/workflows/runs/{run_id}/execute",
            json={"max_loops": 30},
        )
        assert first_execute.status_code == 200
        payload = first_execute.json()
        assert payload["run_status"] == "waiting_approval"
        assert payload["waiting_approval_count"] == 1
        target = payload["waiting_approval_workitem_ids"][0]

        approve = client.post(
            f"/v3/workflows/workitems/{target}/approve",
            json={"approved_by": "owner"},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "ready"

        second_execute = client.post(
            f"/v3/workflows/runs/{run_id}/execute",
            json={"max_loops": 30},
        )
        assert second_execute.status_code == 200
        assert second_execute.json()["run_status"] == "succeeded"
    finally:
        main_module.workflow_engine._release_requires_approval = False
