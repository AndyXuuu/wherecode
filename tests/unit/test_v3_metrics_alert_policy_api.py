import hashlib
import json
from datetime import timedelta

from fastapi.testclient import TestClient

import control_center.main as main_module
from control_center.main import app
from control_center.models.hierarchy import now_utc


client = TestClient(app)


def test_metrics_alert_policy_get_defaults() -> None:
    response = client.get("/metrics/workflows/alert-policy")
    assert response.status_code == 200
    payload = response.json()

    assert payload["failed_run_delta_gt"] == 0
    assert payload["failed_run_count_gte"] == 1
    assert payload["blocked_run_count_gte"] == 2
    assert payload["waiting_approval_count_gte"] == 10
    assert payload["in_flight_command_count_gte"] == 50
    assert payload["audit_count"] == 0
    assert payload["policy_path"].endswith(".json")


def test_metrics_alert_policy_update_and_audit() -> None:
    update = client.put(
        "/metrics/workflows/alert-policy",
        json={
            "failed_run_delta_gt": 2,
            "failed_run_count_gte": 3,
            "blocked_run_count_gte": 4,
            "waiting_approval_count_gte": 7,
            "in_flight_command_count_gte": 21,
            "updated_by": "ops-bot",
            "reason": "raise threshold for rollout",
        },
    )
    assert update.status_code == 200
    updated_payload = update.json()
    assert updated_payload["failed_run_delta_gt"] == 2
    assert updated_payload["audit_count"] == 1

    readback = client.get("/metrics/workflows/alert-policy")
    assert readback.status_code == 200
    assert readback.json()["failed_run_count_gte"] == 3

    audits = client.get("/metrics/workflows/alert-policy/audits")
    assert audits.status_code == 200
    payload = audits.json()
    assert len(payload) == 1
    assert payload[0]["updated_by"] == "ops-bot"
    assert payload[0]["policy"]["in_flight_command_count_gte"] == 21


def test_metrics_verify_policy_registry_get_defaults() -> None:
    response = client.get("/metrics/workflows/alert-policy/verify-policy")
    assert response.status_code == 200
    payload = response.json()
    assert payload["default_profile"] == "standard"
    assert payload["profiles"] == {}
    assert payload["audit_count"] == 0
    assert payload["registry_path"].endswith("metrics_verify_policy_registry.json")


def test_metrics_verify_policy_registry_update_and_export() -> None:
    update = client.put(
        "/metrics/workflows/alert-policy/verify-policy",
        json={
            "default_profile": "strict",
            "profiles": {
                "strict": {
                    "allowed_resolvers": [
                        "manifest_output_path",
                        "archive_basename_fallback",
                    ],
                    "verify_slo_min_pass_rate": 1.0,
                    "verify_slo_max_fetch_failures": 0,
                }
            },
            "updated_by": "ops-admin",
            "reason": "tighten verify policy",
        },
    )
    assert update.status_code == 200
    payload = update.json()
    assert payload["default_profile"] == "strict"
    assert payload["audit_count"] == 1
    assert payload["profiles"]["strict"]["verify_slo_min_pass_rate"] == 1.0

    audits = client.get("/metrics/workflows/alert-policy/verify-policy/audits")
    assert audits.status_code == 200
    audit_entries = audits.json()
    assert len(audit_entries) == 1
    assert audit_entries[0]["updated_by"] == "ops-admin"
    assert audit_entries[0]["registry"]["default_profile"] == "strict"

    export = client.get("/metrics/workflows/alert-policy/verify-policy/export")
    assert export.status_code == 200
    export_payload = export.json()
    assert export_payload["default_profile"] == "strict"
    assert export_payload["source"] == "metrics_verify_policy_registry"
    assert "generated_at" in export_payload


def test_metrics_verify_policy_registry_update_role_guard(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )
    payload = {
        "default_profile": "standard",
        "profiles": {
            "standard": {
                "verify_slo_min_pass_rate": 0.9,
            }
        },
        "updated_by": "ops-admin",
    }

    missing_role = client.put(
        "/metrics/workflows/alert-policy/verify-policy",
        headers={"X-WhereCode-Token": "test-token"},
        json=payload,
    )
    assert missing_role.status_code == 403

    forbidden_role = client.put(
        "/metrics/workflows/alert-policy/verify-policy",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "qa-test",
        },
        json=payload,
    )
    assert forbidden_role.status_code == 403

    mismatch = client.put(
        "/metrics/workflows/alert-policy/verify-policy",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "chief-architect",
        },
        json=payload,
    )
    assert mismatch.status_code == 409

    allowed = client.put(
        "/metrics/workflows/alert-policy/verify-policy",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "ops-admin",
        },
        json=payload,
    )
    assert allowed.status_code == 200
    assert allowed.json()["audit_count"] == 1


def test_metrics_verify_policy_registry_update_invalid_resolver() -> None:
    response = client.put(
        "/metrics/workflows/alert-policy/verify-policy",
        json={
            "default_profile": "strict",
            "profiles": {
                "strict": {
                    "allowed_resolvers": ["manifest_output_path", "bad_resolver"],
                }
            },
            "updated_by": "ops-admin",
        },
    )
    assert response.status_code == 422
    assert "invalid allowed_resolvers" in response.json()["detail"]


def test_metrics_alert_policy_update_role_guard(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    payload = {
        "failed_run_delta_gt": 1,
        "failed_run_count_gte": 1,
        "blocked_run_count_gte": 1,
        "waiting_approval_count_gte": 1,
        "in_flight_command_count_gte": 1,
        "updated_by": "ops-admin",
        "reason": "rbac test",
    }

    missing_role = client.put(
        "/metrics/workflows/alert-policy",
        headers={"X-WhereCode-Token": "test-token"},
        json=payload,
    )
    assert missing_role.status_code == 403

    forbidden_role = client.put(
        "/metrics/workflows/alert-policy",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "qa-test",
        },
        json=payload,
    )
    assert forbidden_role.status_code == 403

    mismatch_actor = client.put(
        "/metrics/workflows/alert-policy",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "chief-architect",
        },
        json=payload,
    )
    assert mismatch_actor.status_code == 409

    allowed = client.put(
        "/metrics/workflows/alert-policy",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "ops-admin",
        },
        json=payload,
    )
    assert allowed.status_code == 200
    assert allowed.json()["audit_count"] == 1

    audits = client.get(
        "/metrics/workflows/alert-policy/audits",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert audits.status_code == 200
    assert audits.json()[0]["updated_by"] == "ops-admin"


def test_metrics_alert_policy_rollback_flow() -> None:
    first = client.put(
        "/metrics/workflows/alert-policy",
        json={
            "failed_run_delta_gt": 1,
            "failed_run_count_gte": 2,
            "blocked_run_count_gte": 3,
            "waiting_approval_count_gte": 4,
            "in_flight_command_count_gte": 5,
            "updated_by": "ops-admin",
            "reason": "seed-a",
        },
    )
    assert first.status_code == 200

    second = client.put(
        "/metrics/workflows/alert-policy",
        json={
            "failed_run_delta_gt": 9,
            "failed_run_count_gte": 8,
            "blocked_run_count_gte": 7,
            "waiting_approval_count_gte": 6,
            "in_flight_command_count_gte": 5,
            "updated_by": "ops-admin",
            "reason": "seed-b",
        },
    )
    assert second.status_code == 200

    audits = client.get("/metrics/workflows/alert-policy/audits")
    assert audits.status_code == 200
    payload = audits.json()
    assert len(payload) >= 2
    source_audit_id = payload[1]["id"]

    dry_run = client.post(
        "/metrics/workflows/alert-policy/rollback",
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "reason": "preview rollback",
            "dry_run": True,
        },
    )
    assert dry_run.status_code == 200
    dry_payload = dry_run.json()
    assert dry_payload["dry_run"] is True
    assert dry_payload["applied"] is False
    assert dry_payload["policy"]["failed_run_count_gte"] == 2

    still_current = client.get("/metrics/workflows/alert-policy").json()
    assert still_current["failed_run_count_gte"] == 8

    apply = client.post(
        "/metrics/workflows/alert-policy/rollback",
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "reason": "apply rollback",
            "dry_run": False,
            "idempotency_key": "rollback-k1",
        },
    )
    assert apply.status_code == 200
    apply_payload = apply.json()
    assert apply_payload["applied"] is True
    assert apply_payload["idempotent_replay"] is False
    assert apply_payload["policy"]["failed_run_count_gte"] == 2

    replay = client.post(
        "/metrics/workflows/alert-policy/rollback",
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "reason": "apply rollback",
            "dry_run": False,
            "idempotency_key": "rollback-k1",
        },
    )
    assert replay.status_code == 200
    replay_payload = replay.json()
    assert replay_payload["applied"] is True
    assert replay_payload["idempotent_replay"] is True
    assert replay_payload["policy"]["failed_run_count_gte"] == 2
    assert replay_payload["audit_count"] == apply_payload["audit_count"]

    no_op_conflict = client.post(
        "/metrics/workflows/alert-policy/rollback",
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "reason": "repeat no idempotency",
            "dry_run": False,
        },
    )
    assert no_op_conflict.status_code == 409

    after = client.get("/metrics/workflows/alert-policy").json()
    assert after["failed_run_count_gte"] == 2

    audits_after = client.get("/metrics/workflows/alert-policy/audits")
    assert audits_after.status_code == 200
    assert audits_after.json()[0]["rollback_from_audit_id"] == source_audit_id
    assert audits_after.json()[0]["rollback_request_id"] == "rollback-k1"


def test_metrics_alert_policy_rollback_idempotency_key_conflict() -> None:
    first = client.put(
        "/metrics/workflows/alert-policy",
        json={
            "failed_run_delta_gt": 1,
            "failed_run_count_gte": 2,
            "blocked_run_count_gte": 3,
            "waiting_approval_count_gte": 4,
            "in_flight_command_count_gte": 5,
            "updated_by": "ops-admin",
            "reason": "seed-a",
        },
    )
    assert first.status_code == 200
    second = client.put(
        "/metrics/workflows/alert-policy",
        json={
            "failed_run_delta_gt": 6,
            "failed_run_count_gte": 7,
            "blocked_run_count_gte": 8,
            "waiting_approval_count_gte": 9,
            "in_flight_command_count_gte": 10,
            "updated_by": "ops-admin",
            "reason": "seed-b",
        },
    )
    assert second.status_code == 200

    audits = client.get("/metrics/workflows/alert-policy/audits").json()
    source_a = audits[1]["id"]
    source_b = audits[0]["id"]

    ok = client.post(
        "/metrics/workflows/alert-policy/rollback",
        json={
            "audit_id": source_a,
            "updated_by": "ops-admin",
            "idempotency_key": "same-key",
        },
    )
    assert ok.status_code == 200

    conflict = client.post(
        "/metrics/workflows/alert-policy/rollback",
        json={
            "audit_id": source_b,
            "updated_by": "ops-admin",
            "idempotency_key": "same-key",
        },
    )
    assert conflict.status_code == 409


def test_metrics_alert_policy_rollback_role_guard(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    seed = client.put(
        "/metrics/workflows/alert-policy",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "ops-admin",
        },
        json={
            "failed_run_delta_gt": 1,
            "failed_run_count_gte": 1,
            "blocked_run_count_gte": 1,
            "waiting_approval_count_gte": 1,
            "in_flight_command_count_gte": 1,
            "updated_by": "ops-admin",
            "reason": "seed for rollback",
        },
    )
    assert seed.status_code == 200
    audits = client.get(
        "/metrics/workflows/alert-policy/audits",
        headers={"X-WhereCode-Token": "test-token"},
    )
    source_audit_id = audits.json()[0]["id"]

    missing_role = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers={"X-WhereCode-Token": "test-token"},
        json={"audit_id": source_audit_id, "updated_by": "ops-admin"},
    )
    assert missing_role.status_code == 403

    forbidden_role = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "qa-test",
        },
        json={"audit_id": source_audit_id, "updated_by": "qa-test"},
    )
    assert forbidden_role.status_code == 403

    mismatch = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "chief-architect",
        },
        json={"audit_id": source_audit_id, "updated_by": "ops-admin"},
    )
    assert mismatch.status_code == 409

    allowed = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "ops-admin",
        },
        json={"audit_id": source_audit_id, "updated_by": "ops-admin", "dry_run": True},
    )
    assert allowed.status_code == 200


def test_metrics_alert_policy_rollback_requires_approval(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(main_module, "METRICS_ROLLBACK_REQUIRES_APPROVAL", True)
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )
    monkeypatch.setattr(
        main_module,
        "METRICS_ROLLBACK_APPROVER_ROLES",
        {"release-manager", "ops-admin"},
    )

    seed_headers = {
        "X-WhereCode-Token": "test-token",
        "X-WhereCode-Role": "ops-admin",
    }
    first = client.put(
        "/metrics/workflows/alert-policy",
        headers=seed_headers,
        json={
            "failed_run_delta_gt": 1,
            "failed_run_count_gte": 2,
            "blocked_run_count_gte": 3,
            "waiting_approval_count_gte": 4,
            "in_flight_command_count_gte": 5,
            "updated_by": "ops-admin",
            "reason": "seed-a",
        },
    )
    assert first.status_code == 200
    second = client.put(
        "/metrics/workflows/alert-policy",
        headers=seed_headers,
        json={
            "failed_run_delta_gt": 6,
            "failed_run_count_gte": 7,
            "blocked_run_count_gte": 8,
            "waiting_approval_count_gte": 9,
            "in_flight_command_count_gte": 10,
            "updated_by": "ops-admin",
            "reason": "seed-b",
        },
    )
    assert second.status_code == 200

    audits = client.get(
        "/metrics/workflows/alert-policy/audits",
        headers={"X-WhereCode-Token": "test-token"},
    ).json()
    source_audit_id = audits[1]["id"]

    no_approval = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers=seed_headers,
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "idempotency_key": "k16-rb-1",
        },
    )
    assert no_approval.status_code == 409

    create_approval = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=seed_headers,
        json={
            "audit_id": source_audit_id,
            "requested_by": "ops-admin",
            "reason": "need rollback",
        },
    )
    assert create_approval.status_code == 201
    approval_id = create_approval.json()["id"]
    assert create_approval.json()["status"] == "pending"

    not_approved = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers=seed_headers,
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "approval_id": approval_id,
            "idempotency_key": "k16-rb-2",
        },
    )
    assert not_approved.status_code == 409

    approve = client.post(
        f"/metrics/workflows/alert-policy/rollback-approvals/{approval_id}/approve",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "release-manager",
        },
        json={"approved_by": "release-manager"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    rollback = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers=seed_headers,
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "approval_id": approval_id,
            "idempotency_key": "k16-rb-3",
        },
    )
    assert rollback.status_code == 200
    assert rollback.json()["applied"] is True

    approvals = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert approvals.status_code == 200
    assert approvals.json()[0]["status"] == "used"

    reseed = client.put(
        "/metrics/workflows/alert-policy",
        headers=seed_headers,
        json={
            "failed_run_delta_gt": 8,
            "failed_run_count_gte": 8,
            "blocked_run_count_gte": 8,
            "waiting_approval_count_gte": 8,
            "in_flight_command_count_gte": 8,
            "updated_by": "ops-admin",
            "reason": "reseed",
        },
    )
    assert reseed.status_code == 200

    reused_approval = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers=seed_headers,
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "approval_id": approval_id,
            "idempotency_key": "k16-rb-4",
        },
    )
    assert reused_approval.status_code == 409


def test_metrics_rollback_approval_expired_rejected(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(main_module, "METRICS_ROLLBACK_REQUIRES_APPROVAL", True)
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )
    monkeypatch.setattr(
        main_module,
        "METRICS_ROLLBACK_APPROVER_ROLES",
        {"release-manager", "ops-admin"},
    )

    headers = {
        "X-WhereCode-Token": "test-token",
        "X-WhereCode-Role": "ops-admin",
    }
    seed = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 2,
            "failed_run_count_gte": 2,
            "blocked_run_count_gte": 2,
            "waiting_approval_count_gte": 2,
            "in_flight_command_count_gte": 2,
            "updated_by": "ops-admin",
            "reason": "seed",
        },
    )
    assert seed.status_code == 200
    audits = client.get(
        "/metrics/workflows/alert-policy/audits",
        headers={"X-WhereCode-Token": "test-token"},
    ).json()
    source_audit_id = audits[0]["id"]

    create = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={
            "audit_id": source_audit_id,
            "requested_by": "ops-admin",
            "reason": "expire me",
        },
    )
    assert create.status_code == 201
    approval_id = create.json()["id"]

    approval_entry = main_module.metrics_alert_policy_store._rollback_approvals[0]
    approval_entry["expires_at"] = now_utc().replace(year=2000)
    main_module.metrics_alert_policy_store._persist_rollback_approvals()

    approve = client.post(
        f"/metrics/workflows/alert-policy/rollback-approvals/{approval_id}/approve",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "release-manager",
        },
        json={"approved_by": "release-manager"},
    )
    assert approve.status_code == 409

    listed = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "expired"


def test_metrics_rollback_approval_stats_and_purge_api(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    headers = {
        "X-WhereCode-Token": "test-token",
        "X-WhereCode-Role": "ops-admin",
    }
    seed = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 3,
            "failed_run_count_gte": 3,
            "blocked_run_count_gte": 3,
            "waiting_approval_count_gte": 3,
            "in_flight_command_count_gte": 3,
            "updated_by": "ops-admin",
            "reason": "seed for stats",
        },
    )
    assert seed.status_code == 200
    reseed = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 7,
            "failed_run_count_gte": 7,
            "blocked_run_count_gte": 7,
            "waiting_approval_count_gte": 7,
            "in_flight_command_count_gte": 7,
            "updated_by": "ops-admin",
            "reason": "reseed for rollback",
        },
    )
    assert reseed.status_code == 200
    audits = client.get(
        "/metrics/workflows/alert-policy/audits",
        headers={"X-WhereCode-Token": "test-token"},
    ).json()
    audit_id = audits[1]["id"]

    pending = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={"audit_id": audit_id, "requested_by": "ops-admin", "reason": "pending"},
    )
    assert pending.status_code == 201
    pending_id = pending.json()["id"]

    approved = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={"audit_id": audit_id, "requested_by": "ops-admin", "reason": "approved"},
    )
    assert approved.status_code == 201
    approved_id = approved.json()["id"]
    approved_action = client.post(
        f"/metrics/workflows/alert-policy/rollback-approvals/{approved_id}/approve",
        headers=headers,
        json={"approved_by": "ops-admin"},
    )
    assert approved_action.status_code == 200

    used = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={"audit_id": audit_id, "requested_by": "ops-admin", "reason": "used"},
    )
    assert used.status_code == 201
    used_id = used.json()["id"]
    approve_used = client.post(
        f"/metrics/workflows/alert-policy/rollback-approvals/{used_id}/approve",
        headers=headers,
        json={"approved_by": "ops-admin"},
    )
    assert approve_used.status_code == 200
    rollback_used = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers=headers,
        json={
            "audit_id": audit_id,
            "updated_by": "ops-admin",
            "approval_id": used_id,
            "idempotency_key": "k18-stats-used",
        },
    )
    assert rollback_used.status_code == 200

    expired = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={"audit_id": audit_id, "requested_by": "ops-admin", "reason": "expired"},
    )
    assert expired.status_code == 201
    expired_id = expired.json()["id"]

    for entry in main_module.metrics_alert_policy_store._rollback_approvals:
        if entry["id"] == expired_id:
            entry["expires_at"] = now_utc().replace(year=2000)
            break
    main_module.metrics_alert_policy_store._persist_rollback_approvals()

    stats = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/stats",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert stats.status_code == 200
    assert stats.json() == {
        "total": 4,
        "pending": 1,
        "approved": 1,
        "rejected": 0,
        "used": 1,
        "expired": 1,
    }

    dry_run = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge",
        headers=headers,
        json={
            "requested_by": "ops-admin",
            "remove_used": True,
            "remove_expired": True,
            "dry_run": True,
        },
    )
    assert dry_run.status_code == 200
    assert dry_run.json()["purge_audit_id"]
    assert dry_run.json()["removed_total"] == 2
    assert dry_run.json()["remaining_total"] == 2

    stats_after_dry_run = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/stats",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert stats_after_dry_run.status_code == 200
    assert stats_after_dry_run.json()["total"] == 4

    apply = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge",
        headers=headers,
        json={
            "requested_by": "ops-admin",
            "remove_used": True,
            "remove_expired": True,
            "dry_run": False,
        },
    )
    assert apply.status_code == 200
    assert apply.json()["purge_audit_id"]
    assert apply.json()["removed_total"] == 2
    assert apply.json()["remaining_total"] == 2

    stats_after_apply = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/stats",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert stats_after_apply.status_code == 200
    assert stats_after_apply.json() == {
        "total": 2,
        "pending": 1,
        "approved": 1,
        "rejected": 0,
        "used": 0,
        "expired": 0,
    }
    remaining_ids = {
        item["id"]
        for item in client.get(
            "/metrics/workflows/alert-policy/rollback-approvals",
            headers={"X-WhereCode-Token": "test-token"},
        ).json()
    }
    assert pending_id in remaining_ids
    assert approved_id in remaining_ids
    assert used_id not in remaining_ids
    assert expired_id not in remaining_ids

    purge_audits = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert purge_audits.status_code == 200
    assert len(purge_audits.json()) >= 2
    assert purge_audits.json()[0]["requested_by"] == "ops-admin"


def test_metrics_rollback_approval_purge_role_guard(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    missing_role = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge",
        headers={"X-WhereCode-Token": "test-token"},
        json={"requested_by": "ops-admin"},
    )
    assert missing_role.status_code == 403

    forbidden = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "qa-test",
        },
        json={"requested_by": "qa-test"},
    )
    assert forbidden.status_code == 403

    mismatch = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "chief-architect",
        },
        json={"requested_by": "ops-admin"},
    )
    assert mismatch.status_code == 409


def test_metrics_rollback_approval_purge_older_than_window(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    headers = {
        "X-WhereCode-Token": "test-token",
        "X-WhereCode-Role": "ops-admin",
    }
    first = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 1,
            "failed_run_count_gte": 1,
            "blocked_run_count_gte": 1,
            "waiting_approval_count_gte": 1,
            "in_flight_command_count_gte": 1,
            "updated_by": "ops-admin",
            "reason": "seed-a",
        },
    )
    assert first.status_code == 200
    second = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 4,
            "failed_run_count_gte": 4,
            "blocked_run_count_gte": 4,
            "waiting_approval_count_gte": 4,
            "in_flight_command_count_gte": 4,
            "updated_by": "ops-admin",
            "reason": "seed-b",
        },
    )
    assert second.status_code == 200

    audits = client.get(
        "/metrics/workflows/alert-policy/audits",
        headers={"X-WhereCode-Token": "test-token"},
    ).json()
    source_audit_id = audits[1]["id"]

    used = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={"audit_id": source_audit_id, "requested_by": "ops-admin", "reason": "used"},
    )
    assert used.status_code == 201
    used_id = used.json()["id"]
    approve_used = client.post(
        f"/metrics/workflows/alert-policy/rollback-approvals/{used_id}/approve",
        headers=headers,
        json={"approved_by": "ops-admin"},
    )
    assert approve_used.status_code == 200
    rollback_used = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers=headers,
        json={
            "audit_id": source_audit_id,
            "updated_by": "ops-admin",
            "approval_id": used_id,
            "idempotency_key": "k19-used",
        },
    )
    assert rollback_used.status_code == 200

    expired = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={"audit_id": source_audit_id, "requested_by": "ops-admin", "reason": "expired"},
    )
    assert expired.status_code == 201
    expired_id = expired.json()["id"]

    old_time = now_utc() - timedelta(seconds=7200)
    for entry in main_module.metrics_alert_policy_store._rollback_approvals:
        if entry["id"] == expired_id:
            entry["status"] = "expired"
            entry["updated_at"] = old_time
            entry["expires_at"] = now_utc().replace(year=2000)
            break
    main_module.metrics_alert_policy_store._persist_rollback_approvals()

    apply = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge",
        headers=headers,
        json={
            "requested_by": "ops-admin",
            "remove_used": True,
            "remove_expired": True,
            "older_than_seconds": 3600,
        },
    )
    assert apply.status_code == 200
    assert apply.json()["removed_used"] == 0
    assert apply.json()["removed_expired"] == 1
    assert apply.json()["removed_total"] == 1
    assert apply.json()["remaining_total"] == 1
    assert apply.json()["older_than_seconds"] == 3600
    assert apply.json()["purge_audit_id"]

    remaining = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert remaining.status_code == 200
    assert len(remaining.json()) == 1
    assert remaining.json()[0]["id"] == used_id

    purge_audits = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits?limit=1",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert purge_audits.status_code == 200
    assert len(purge_audits.json()) == 1
    assert purge_audits.json()[0]["older_than_seconds"] == 3600


def test_metrics_rollback_approval_purge_audits_gc(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    headers = {
        "X-WhereCode-Token": "test-token",
        "X-WhereCode-Role": "ops-admin",
    }
    seed = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 5,
            "failed_run_count_gte": 5,
            "blocked_run_count_gte": 5,
            "waiting_approval_count_gte": 5,
            "in_flight_command_count_gte": 5,
            "updated_by": "ops-admin",
            "reason": "seed",
        },
    )
    assert seed.status_code == 200
    reseed = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 9,
            "failed_run_count_gte": 9,
            "blocked_run_count_gte": 9,
            "waiting_approval_count_gte": 9,
            "in_flight_command_count_gte": 9,
            "updated_by": "ops-admin",
            "reason": "reseed",
        },
    )
    assert reseed.status_code == 200
    audits = client.get(
        "/metrics/workflows/alert-policy/audits",
        headers={"X-WhereCode-Token": "test-token"},
    ).json()
    audit_id = audits[1]["id"]

    approval = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        headers=headers,
        json={"audit_id": audit_id, "requested_by": "ops-admin", "reason": "seed-approval"},
    )
    assert approval.status_code == 201
    approval_id = approval.json()["id"]
    approve = client.post(
        f"/metrics/workflows/alert-policy/rollback-approvals/{approval_id}/approve",
        headers=headers,
        json={"approved_by": "ops-admin"},
    )
    assert approve.status_code == 200
    rollback = client.post(
        "/metrics/workflows/alert-policy/rollback",
        headers=headers,
        json={
            "audit_id": audit_id,
            "updated_by": "ops-admin",
            "approval_id": approval_id,
            "idempotency_key": "k21-seed",
        },
    )
    assert rollback.status_code == 200

    for _ in range(3):
        purge_resp = client.post(
            "/metrics/workflows/alert-policy/rollback-approvals/purge",
            headers=headers,
            json={
                "requested_by": "ops-admin",
                "remove_used": True,
                "remove_expired": True,
                "dry_run": True,
            },
        )
        assert purge_resp.status_code == 200

    old_time = now_utc() - timedelta(seconds=7200)
    for idx, entry in enumerate(main_module.metrics_alert_policy_store._rollback_approval_purge_audits):
        if idx < 2:
            entry["created_at"] = old_time
    main_module.metrics_alert_policy_store._persist_rollback_approval_purge_audits()

    safety = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        headers=headers,
        json={"requested_by": "ops-admin"},
    )
    assert safety.status_code == 409

    dry_run = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        headers=headers,
        json={
            "requested_by": "ops-admin",
            "dry_run": True,
            "older_than_seconds": 3600,
            "keep_latest": 1,
        },
    )
    assert dry_run.status_code == 200
    assert dry_run.json()["removed_total"] == 2
    assert dry_run.json()["remaining_total"] >= 1
    assert dry_run.json()["purge_audit_gc_id"]

    apply = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        headers=headers,
        json={
            "requested_by": "ops-admin",
            "dry_run": False,
            "older_than_seconds": 3600,
            "keep_latest": 1,
        },
    )
    assert apply.status_code == 200
    assert apply.json()["removed_total"] == 2
    assert apply.json()["purge_audit_gc_id"]

    remaining = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits?limit=20",
        headers={"X-WhereCode-Token": "test-token"},
    )
    assert remaining.status_code == 200
    assert remaining.json()[0]["event_type"] == "purge_audit_gc"


def test_metrics_rollback_approval_purge_audits_gc_role_guard(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    missing_role = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        headers={"X-WhereCode-Token": "test-token"},
        json={"requested_by": "ops-admin", "older_than_seconds": 3600},
    )
    assert missing_role.status_code == 403

    forbidden = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "qa-test",
        },
        json={"requested_by": "qa-test", "older_than_seconds": 3600},
    )
    assert forbidden.status_code == 403

    mismatch = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        headers={
            "X-WhereCode-Token": "test-token",
            "X-WhereCode-Role": "chief-architect",
        },
        json={"requested_by": "ops-admin", "older_than_seconds": 3600},
    )
    assert mismatch.status_code == 409


def test_metrics_rollback_approval_purge_audits_export(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        main_module,
        "METRICS_ALERT_POLICY_UPDATE_ROLES",
        {"ops-admin", "chief-architect"},
    )

    headers = {
        "X-WhereCode-Token": "test-token",
        "X-WhereCode-Role": "ops-admin",
    }
    seed = client.put(
        "/metrics/workflows/alert-policy",
        headers=headers,
        json={
            "failed_run_delta_gt": 10,
            "failed_run_count_gte": 10,
            "blocked_run_count_gte": 10,
            "waiting_approval_count_gte": 10,
            "in_flight_command_count_gte": 10,
            "updated_by": "ops-admin",
            "reason": "seed-export",
        },
    )
    assert seed.status_code == 200
    for _ in range(2):
        purge_resp = client.post(
            "/metrics/workflows/alert-policy/rollback-approvals/purge",
            headers=headers,
            json={
                "requested_by": "ops-admin",
                "remove_used": True,
                "remove_expired": True,
                "dry_run": True,
            },
        )
        assert purge_resp.status_code == 200

    old_time = now_utc() - timedelta(seconds=7200)
    for idx, entry in enumerate(main_module.metrics_alert_policy_store._rollback_approval_purge_audits):
        if idx == 0:
            entry["created_at"] = old_time
    main_module.metrics_alert_policy_store._persist_rollback_approval_purge_audits()

    gc = client.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        headers=headers,
        json={
            "requested_by": "ops-admin",
            "dry_run": True,
            "older_than_seconds": 3600,
            "keep_latest": 0,
        },
    )
    assert gc.status_code == 200

    export_old = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/export",
        headers={"X-WhereCode-Token": "test-token"},
        params={
            "event_type": "approval_purge",
            "created_before": (now_utc() - timedelta(seconds=3600)).isoformat(),
            "limit": 20,
        },
    )
    assert export_old.status_code == 200
    assert export_old.json()["exported_total"] >= 1
    assert export_old.json()["event_type"] == "approval_purge"
    assert export_old.json()["checksum_scope"] == "entries"
    checksum_old = hashlib.sha256(
        json.dumps(
            export_old.json()["entries"],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert export_old.json()["checksum_sha256"] == checksum_old
    assert all(
        item["event_type"] == "approval_purge"
        for item in export_old.json()["entries"]
    )

    export_gc = client.get(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/export",
        headers={"X-WhereCode-Token": "test-token"},
        params={"event_type": "purge_audit_gc", "limit": 20},
    )
    assert export_gc.status_code == 200
    assert export_gc.json()["exported_total"] >= 1
    checksum_gc = hashlib.sha256(
        json.dumps(
            export_gc.json()["entries"],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert export_gc.json()["checksum_sha256"] == checksum_gc
    assert export_gc.json()["entries"][0]["event_type"] == "purge_audit_gc"
