from __future__ import annotations

from datetime import timedelta

from control_center.models.hierarchy import new_id, now_utc
from control_center.services.metrics_alert_policy_store_errors import (
    PolicyRollbackApprovalError,
    PolicyRollbackConflictError,
)
from control_center.services.metrics_alert_policy_store_policy import (
    build_rollback_approval_stats,
    compute_rollback_approval_purge_audit_gc_result,
    compute_rollback_approval_purge_result,
    filter_rollback_approval_purge_audits,
    filter_rollback_approvals_by_status,
)


def rollback_to_audit(
    store,
    audit_id: str,
    *,
    updated_by: str,
    reason: str | None = None,
    dry_run: bool = False,
    idempotency_key: str | None = None,
    approval_id: str | None = None,
) -> dict[str, object]:
    target = store.get_audit(audit_id)
    if target is None:
        raise KeyError(f"audit not found: {audit_id}")

    payload = target.get("policy")
    if not isinstance(payload, dict):
        raise ValueError(f"audit has no policy payload: {audit_id}")
    normalized = store._normalize_policy(payload)
    request_id = (idempotency_key or "").strip()

    if request_id:
        replay = store._find_rollback_by_request_id(request_id)
        if replay is not None:
            replay_source = str(replay.get("rollback_from_audit_id", "")).strip()
            if replay_source and replay_source != audit_id:
                raise PolicyRollbackConflictError(
                    "idempotency key already used by another rollback target"
                )
            replay_policy = replay.get("policy")
            if not isinstance(replay_policy, dict):
                replay_policy = {}
            return {
                "source_audit_id": audit_id,
                "dry_run": dry_run,
                "applied": True,
                "idempotent_replay": True,
                "policy": store._normalize_policy(replay_policy),
                "policy_path": str(store._policy_path),
                "audit_count": len(store._audit_entries),
            }

    if normalized == store._policy:
        if dry_run:
            return {
                "source_audit_id": audit_id,
                "dry_run": True,
                "applied": False,
                "idempotent_replay": False,
                "policy": normalized,
                "policy_path": str(store._policy_path),
                "audit_count": len(store._audit_entries),
            }
        raise PolicyRollbackConflictError("policy already matches rollback target")

    if dry_run:
        return {
            "source_audit_id": audit_id,
            "dry_run": True,
            "applied": False,
            "idempotent_replay": False,
            "policy": normalized,
            "policy_path": str(store._policy_path),
            "audit_count": len(store._audit_entries),
        }

    if approval_id is not None:
        normalized_approval_id = approval_id.strip()
        if not normalized_approval_id:
            raise PolicyRollbackApprovalError("rollback approval id is empty")
        store.consume_rollback_approval(
            normalized_approval_id,
            audit_id=audit_id,
            used_by=updated_by.strip(),
        )
    else:
        normalized_approval_id = None

    store._policy = normalized
    store._updated_at = now_utc()
    store._policy_path.parent.mkdir(parents=True, exist_ok=True)
    store._policy_path.write_text(
        __import__("json").dumps(store._policy, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    entry = {
        "id": new_id("map"),
        "updated_at": store._updated_at,
        "updated_by": updated_by.strip(),
        "reason": reason,
        "rollback_from_audit_id": audit_id,
        "rollback_request_id": request_id or None,
        "rollback_approval_id": normalized_approval_id,
        "policy": dict(store._policy),
    }
    store._audit_entries.append(entry)
    store._append_audit(entry)
    return {
        "source_audit_id": audit_id,
        "dry_run": False,
        "applied": True,
        "idempotent_replay": False,
        "policy": dict(store._policy),
        "policy_path": str(store._policy_path),
        "audit_count": len(store._audit_entries),
    }


def create_rollback_approval(
    store,
    *,
    audit_id: str,
    requested_by: str,
    reason: str | None = None,
) -> dict[str, object]:
    if store.get_audit(audit_id) is None:
        raise KeyError(f"audit not found: {audit_id}")
    now = now_utc()
    expires_at = now + timedelta(seconds=store._rollback_approval_ttl_seconds)
    entry = {
        "id": new_id("rap"),
        "audit_id": audit_id,
        "status": "pending",
        "requested_by": requested_by.strip(),
        "approved_by": None,
        "used_by": None,
        "reason": reason,
        "created_at": now,
        "updated_at": now,
        "expires_at": expires_at,
    }
    store._rollback_approvals.append(entry)
    store._persist_rollback_approvals()
    return dict(entry)


def approve_rollback_approval(
    store,
    approval_id: str,
    *,
    approved_by: str,
) -> dict[str, object]:
    store._refresh_rollback_approval_statuses()
    approval = store._find_rollback_approval(approval_id)
    if approval is None:
        raise KeyError(f"rollback approval not found: {approval_id}")
    status = str(approval.get("status", "")).strip()
    if status == "approved":
        return dict(approval)
    if status == "expired":
        raise PolicyRollbackApprovalError(f"rollback approval expired: {approval_id}")
    if status != "pending":
        raise PolicyRollbackApprovalError(
            f"rollback approval is not pending: {approval_id}"
        )

    approval["status"] = "approved"
    approval["approved_by"] = approved_by.strip()
    approval["updated_at"] = now_utc()
    store._persist_rollback_approvals()
    return dict(approval)


def consume_rollback_approval(
    store,
    approval_id: str,
    *,
    audit_id: str,
    used_by: str,
) -> dict[str, object]:
    store._refresh_rollback_approval_statuses()
    approval = store._find_rollback_approval(approval_id)
    if approval is None:
        raise KeyError(f"rollback approval not found: {approval_id}")

    request_audit_id = str(approval.get("audit_id", "")).strip()
    if request_audit_id != audit_id:
        raise PolicyRollbackApprovalError("rollback approval is bound to another audit id")

    status = str(approval.get("status", "")).strip()
    if status == "used":
        raise PolicyRollbackConflictError(f"rollback approval already used: {approval_id}")
    if status == "expired":
        raise PolicyRollbackApprovalError(f"rollback approval expired: {approval_id}")
    if status != "approved":
        raise PolicyRollbackApprovalError(
            f"rollback approval is not approved: {approval_id}"
        )

    approval["status"] = "used"
    approval["used_by"] = used_by.strip()
    approval["updated_at"] = now_utc()
    store._persist_rollback_approvals()
    return dict(approval)


def list_rollback_approvals(
    store,
    *,
    limit: int = 20,
    status: str | None = None,
) -> list[dict[str, object]]:
    store._refresh_rollback_approval_statuses()
    if limit < 1:
        return []
    records = filter_rollback_approvals_by_status(store._rollback_approvals, status=status)
    return list(reversed(records[-limit:]))


def get_rollback_approval_stats(store) -> dict[str, int]:
    store._refresh_rollback_approval_statuses()
    return build_rollback_approval_stats(store._rollback_approvals)


def purge_rollback_approvals(
    store,
    *,
    remove_used: bool = True,
    remove_expired: bool = True,
    dry_run: bool = False,
    older_than_seconds: int | None = None,
    requested_by: str | None = None,
) -> dict[str, object]:
    store._refresh_rollback_approval_statuses(persist=not dry_run)
    now = now_utc() if older_than_seconds is not None else None
    keep, removed_used, removed_expired = compute_rollback_approval_purge_result(
        store._rollback_approvals,
        remove_used=remove_used,
        remove_expired=remove_expired,
        older_than_seconds=older_than_seconds,
        now=now,
        is_older_than_handler=store._is_older_than,
    )

    if not dry_run:
        store._rollback_approvals = keep
        if removed_used or removed_expired:
            store._persist_rollback_approvals()

    result: dict[str, object] = {
        "removed_used": removed_used,
        "removed_expired": removed_expired,
        "removed_total": removed_used + removed_expired,
        "remaining_total": len(keep),
    }
    actor = (requested_by or "").strip()
    if actor:
        audit_entry = {
            "id": new_id("rpg"),
            "event_type": "approval_purge",
            "requested_by": actor,
            "dry_run": dry_run,
            "remove_used": remove_used,
            "remove_expired": remove_expired,
            "older_than_seconds": older_than_seconds,
            "removed_used": removed_used,
            "removed_expired": removed_expired,
            "removed_total": removed_used + removed_expired,
            "remaining_total": len(keep),
            "created_at": now_utc(),
        }
        store._rollback_approval_purge_audits.append(audit_entry)
        store._append_rollback_approval_purge_audit(audit_entry)
        result["purge_audit_id"] = str(audit_entry["id"])
    return result


def list_rollback_approval_purge_audits(
    store,
    *,
    limit: int = 20,
    event_type: str | None = None,
    created_after=None,
    created_before=None,
) -> list[dict[str, object]]:
    if limit < 1:
        return []
    records = filter_rollback_approval_purge_audits(
        store._rollback_approval_purge_audits,
        event_type=event_type,
        created_after=created_after,
        created_before=created_before,
        is_timestamp_after_handler=store._is_timestamp_after,
        is_timestamp_before_handler=store._is_timestamp_before,
    )
    return list(reversed(records[-limit:]))


def purge_rollback_approval_purge_audits(
    store,
    *,
    dry_run: bool = False,
    older_than_seconds: int | None = None,
    keep_latest: int = 0,
    requested_by: str | None = None,
) -> dict[str, object]:
    now = now_utc() if older_than_seconds is not None else None
    keep, removed_total, latest_to_keep = compute_rollback_approval_purge_audit_gc_result(
        store._rollback_approval_purge_audits,
        older_than_seconds=older_than_seconds,
        keep_latest=keep_latest,
        now=now,
        is_older_than_handler=store._is_older_than,
    )

    if not dry_run:
        store._rollback_approval_purge_audits = keep
        if removed_total:
            store._persist_rollback_approval_purge_audits()

    result: dict[str, object] = {
        "removed_total": removed_total,
        "remaining_total": len(keep),
    }
    actor = (requested_by or "").strip()
    if actor:
        audit_entry = {
            "id": new_id("rpg"),
            "event_type": "purge_audit_gc",
            "requested_by": actor,
            "dry_run": dry_run,
            "older_than_seconds": older_than_seconds,
            "keep_latest": latest_to_keep,
            "removed_total": removed_total,
            "remaining_total": len(keep),
            "created_at": now_utc(),
        }
        store._rollback_approval_purge_audits.append(audit_entry)
        store._append_rollback_approval_purge_audit(audit_entry)
        result["purge_audit_gc_id"] = str(audit_entry["id"])
    return result
