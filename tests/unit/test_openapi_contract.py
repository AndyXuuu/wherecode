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
        "/metrics/summary": {"get"},
        "/metrics/workflows": {"get"},
        "/metrics/workflows/alert-policy": {"get", "put"},
        "/metrics/workflows/alert-policy/verify-policy": {"get", "put"},
        "/metrics/workflows/alert-policy/verify-policy/audits": {"get"},
        "/metrics/workflows/alert-policy/verify-policy/export": {"get"},
        "/metrics/workflows/alert-policy/rollback": {"post"},
        "/metrics/workflows/alert-policy/rollback-approvals": {"get", "post"},
        "/metrics/workflows/alert-policy/rollback-approvals/stats": {"get"},
        "/metrics/workflows/alert-policy/rollback-approvals/purge": {"post"},
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits": {"get"},
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/export": {"get"},
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge": {"post"},
        "/metrics/workflows/alert-policy/rollback-approvals/{approval_id}/approve": {"post"},
        "/metrics/workflows/alert-policy/audits": {"get"},
        "/agent-routing": {"get", "put"},
        "/agent-routing/reload": {"post"},
        "/v3/workflows/runs": {"post"},
        "/v3/workflows/runs/{run_id}": {"get"},
        "/v3/workflows/runs/{run_id}/workitems": {"get", "post"},
        "/v3/workflows/runs/{run_id}/gates": {"get"},
        "/v3/workflows/runs/{run_id}/artifacts": {"get"},
        "/v3/workflows/runs/{run_id}/tick": {"post"},
        "/v3/workflows/runs/{run_id}/bootstrap": {"post"},
        "/v3/workflows/runs/{run_id}/execute": {"post"},
        "/v3/workflows/workitems/{workitem_id}/start": {"post"},
        "/v3/workflows/workitems/{workitem_id}/approve": {"post"},
        "/v3/workflows/workitems/{workitem_id}/complete": {"post"},
        "/v3/workflows/workitems/{workitem_id}/discussions": {"get"},
        "/v3/workflows/workitems/{workitem_id}/discussion/resolve": {"post"},
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

    action_execute = schemas["ActionExecuteRequest"]
    action_execute_props = action_execute["properties"]
    assert "agent" in action_execute_props
    assert "role" in action_execute_props
    assert "module_key" in action_execute_props

    action_execute_response = schemas["ActionExecuteResponse"]
    assert "discussion" in action_execute_response["properties"]

    approve_command = schemas["ApproveCommandRequest"]
    assert "approved_by" in approve_command["properties"]
    assert "approved_by" in approve_command["required"]

    create_task = schemas["CreateTaskRequest"]
    create_task_props = create_task["properties"]
    assert "assignee_agent" in create_task_props
    assert create_task_props["assignee_agent"].get("default") == "auto-agent"

    metrics_summary = schemas["MetricsSummaryResponse"]
    metrics_props = metrics_summary["properties"]
    assert "executor_agent_counts" in metrics_props
    assert "routing_reason_counts" in metrics_props
    assert "routing_keyword_counts" in metrics_props
    assert "routing_rule_counts" in metrics_props
    assert "recent_windows" in metrics_props

    workflow_metrics = schemas["WorkflowMetricsResponse"]
    workflow_metrics_props = workflow_metrics["properties"]
    assert "total_runs" in workflow_metrics_props
    assert "run_status_counts" in workflow_metrics_props
    assert "total_workitems" in workflow_metrics_props
    assert "total_gate_checks" in workflow_metrics_props

    metrics_alert_policy = schemas["MetricsAlertPolicyResponse"]
    assert "failed_run_delta_gt" in metrics_alert_policy["properties"]
    assert "policy_path" in metrics_alert_policy["properties"]
    assert "audit_count" in metrics_alert_policy["properties"]

    metrics_alert_update = schemas["MetricsAlertPolicyUpdateRequest"]
    assert "updated_by" in metrics_alert_update["required"]

    metrics_alert_audit_entry = schemas["MetricsAlertPolicyAuditEntry"]
    assert "updated_by" in metrics_alert_audit_entry["properties"]
    assert "policy" in metrics_alert_audit_entry["properties"]
    assert "rollback_from_audit_id" in metrics_alert_audit_entry["properties"]
    assert "rollback_request_id" in metrics_alert_audit_entry["properties"]
    assert "rollback_approval_id" in metrics_alert_audit_entry["properties"]

    verify_policy_profile_config = schemas["VerifyPolicyProfileConfig"]
    assert "allowed_resolvers" in verify_policy_profile_config["properties"]
    assert "verify_slo_min_pass_rate" in verify_policy_profile_config["properties"]

    verify_policy_registry_response = schemas["VerifyPolicyRegistryResponse"]
    assert "default_profile" in verify_policy_registry_response["properties"]
    assert "profiles" in verify_policy_registry_response["properties"]
    assert "registry_path" in verify_policy_registry_response["properties"]
    assert "updated_at" in verify_policy_registry_response["properties"]

    verify_policy_registry_update_request = schemas["VerifyPolicyRegistryUpdateRequest"]
    assert "updated_by" in verify_policy_registry_update_request["required"]
    assert "profiles" in verify_policy_registry_update_request["properties"]

    verify_policy_registry_audit_entry = schemas["VerifyPolicyRegistryAuditEntry"]
    assert "updated_by" in verify_policy_registry_audit_entry["properties"]
    assert "registry" in verify_policy_registry_audit_entry["properties"]

    verify_policy_registry_export = schemas["VerifyPolicyRegistryExportResponse"]
    assert "generated_at" in verify_policy_registry_export["properties"]
    assert "source" in verify_policy_registry_export["properties"]

    rollback_metrics_alert_policy_request = schemas["RollbackMetricsAlertPolicyRequest"]
    assert "audit_id" in rollback_metrics_alert_policy_request["required"]
    assert "updated_by" in rollback_metrics_alert_policy_request["required"]
    assert "idempotency_key" in rollback_metrics_alert_policy_request["properties"]
    assert "approval_id" in rollback_metrics_alert_policy_request["properties"]

    rollback_metrics_alert_policy_response = schemas["RollbackMetricsAlertPolicyResponse"]
    assert "source_audit_id" in rollback_metrics_alert_policy_response["properties"]
    assert "applied" in rollback_metrics_alert_policy_response["properties"]
    assert "idempotent_replay" in rollback_metrics_alert_policy_response["properties"]
    assert "policy" in rollback_metrics_alert_policy_response["properties"]

    rollback_approval_request = schemas["CreateRollbackApprovalRequest"]
    assert "audit_id" in rollback_approval_request["required"]
    assert "requested_by" in rollback_approval_request["required"]

    approve_rollback_approval_request = schemas["ApproveRollbackApprovalRequest"]
    assert "approved_by" in approve_rollback_approval_request["required"]

    rollback_approval_response = schemas["RollbackApprovalResponse"]
    assert "status" in rollback_approval_response["properties"]
    assert "approved_by" in rollback_approval_response["properties"]
    assert "expires_at" in rollback_approval_response["properties"]

    rollback_approval_stats = schemas["RollbackApprovalStatsResponse"]
    assert "total" in rollback_approval_stats["properties"]
    assert "expired" in rollback_approval_stats["properties"]

    purge_rollback_approvals_request = schemas["PurgeRollbackApprovalsRequest"]
    assert "requested_by" in purge_rollback_approvals_request["required"]
    assert "remove_used" in purge_rollback_approvals_request["properties"]
    assert "older_than_seconds" in purge_rollback_approvals_request["properties"]

    purge_rollback_approvals_response = schemas["PurgeRollbackApprovalsResponse"]
    assert "removed_total" in purge_rollback_approvals_response["properties"]
    assert "remaining_total" in purge_rollback_approvals_response["properties"]
    assert "older_than_seconds" in purge_rollback_approvals_response["properties"]
    assert "purge_audit_id" in purge_rollback_approvals_response["properties"]

    purge_rollback_approvals_audit_entry = schemas["PurgeRollbackApprovalsAuditEntry"]
    assert "event_type" in purge_rollback_approvals_audit_entry["properties"]
    assert "requested_by" in purge_rollback_approvals_audit_entry["properties"]
    assert "keep_latest" in purge_rollback_approvals_audit_entry["properties"]
    assert "created_at" in purge_rollback_approvals_audit_entry["properties"]

    purge_rollback_approval_purge_audits_request = schemas["PurgeRollbackApprovalPurgeAuditsRequest"]
    assert "requested_by" in purge_rollback_approval_purge_audits_request["required"]
    assert "older_than_seconds" in purge_rollback_approval_purge_audits_request["properties"]
    assert "keep_latest" in purge_rollback_approval_purge_audits_request["properties"]

    purge_rollback_approval_purge_audits_response = schemas["PurgeRollbackApprovalPurgeAuditsResponse"]
    assert "removed_total" in purge_rollback_approval_purge_audits_response["properties"]
    assert "remaining_total" in purge_rollback_approval_purge_audits_response["properties"]
    assert "purge_audit_gc_id" in purge_rollback_approval_purge_audits_response["properties"]

    export_rollback_approval_purge_audits_response = schemas["ExportRollbackApprovalPurgeAuditsResponse"]
    assert "exported_total" in export_rollback_approval_purge_audits_response["properties"]
    assert "generated_at" in export_rollback_approval_purge_audits_response["properties"]
    assert "checksum_scope" in export_rollback_approval_purge_audits_response["properties"]
    assert "checksum_sha256" in export_rollback_approval_purge_audits_response["properties"]
    assert "entries" in export_rollback_approval_purge_audits_response["properties"]

    rollback_approval_status = schemas["RollbackApprovalStatus"]
    assert "expired" in rollback_approval_status["enum"]

    create_workflow_run = schemas["CreateWorkflowRunRequest"]
    assert "project_id" in create_workflow_run["required"]

    create_workitem = schemas["CreateWorkItemRequest"]
    create_workitem_props = create_workitem["properties"]
    assert create_workitem_props["assignee_agent"].get("default") == "auto-agent"
    assert create_workitem_props["discussion_budget"].get("default") == 2

    complete_workitem = schemas["CompleteWorkItemRequest"]
    assert "success" in complete_workitem["required"]

    bootstrap_workflow = schemas["BootstrapWorkflowRequest"]
    assert "modules" in bootstrap_workflow["required"]

    execute_workflow = schemas["ExecuteWorkflowRunRequest"]
    assert execute_workflow["properties"]["max_loops"].get("default") == 20

    execute_workflow_response = schemas["ExecuteWorkflowRunResponse"]
    assert "waiting_discussion_count" in execute_workflow_response["properties"]
    assert "waiting_discussion_workitem_ids" in execute_workflow_response["properties"]
    assert "waiting_approval_count" in execute_workflow_response["properties"]
    assert "waiting_approval_workitem_ids" in execute_workflow_response["properties"]

    resolve_discussion = schemas["ResolveDiscussionRequest"]
    assert "decision" in resolve_discussion["required"]
    assert "resolved_by" in resolve_discussion["required"]

    approve_workitem = schemas["ApproveWorkItemRequest"]
    assert "approved_by" in approve_workitem["required"]
