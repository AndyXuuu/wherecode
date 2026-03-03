from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from control_center.models.hierarchy import new_id, now_utc


DEFAULT_POLICY: dict[str, int] = {
    "failed_run_delta_gt": 0,
    "failed_run_count_gte": 1,
    "blocked_run_count_gte": 2,
    "waiting_approval_count_gte": 10,
    "in_flight_command_count_gte": 50,
}

VERIFY_POLICY_ALLOWED_RESOLVERS = {
    "manifest_output_path",
    "manifest_file_uri",
    "archive_basename_fallback",
    "archive_relative_fallback",
    "fetch_hook",
}

DEFAULT_VERIFY_POLICY_REGISTRY: dict[str, object] = {
    "default_profile": "standard",
    "profiles": {},
}


class PolicyRollbackConflictError(ValueError):
    pass


class PolicyRollbackApprovalError(ValueError):
    pass


class MetricsAlertPolicyStore:
    def __init__(
        self,
        policy_path: str,
        audit_path: str,
        rollback_approval_path: str | None = None,
        rollback_approval_purge_audit_path: str | None = None,
        verify_policy_registry_path: str | None = None,
        verify_policy_registry_audit_path: str | None = None,
        rollback_approval_ttl_seconds: int = 86400,
    ) -> None:
        self._policy_path = Path(policy_path)
        self._audit_path = Path(audit_path)
        self._rollback_approval_path = (
            Path(rollback_approval_path)
            if rollback_approval_path is not None
            else self._audit_path.with_name("metrics_rollback_approvals.jsonl")
        )
        self._rollback_approval_purge_audit_path = (
            Path(rollback_approval_purge_audit_path)
            if rollback_approval_purge_audit_path is not None
            else self._audit_path.with_name("metrics_rollback_approval_purge_audit.jsonl")
        )
        self._verify_policy_registry_path = (
            Path(verify_policy_registry_path)
            if verify_policy_registry_path is not None
            else self._policy_path.with_name("metrics_verify_policy_registry.json")
        )
        self._verify_policy_registry_audit_path = (
            Path(verify_policy_registry_audit_path)
            if verify_policy_registry_audit_path is not None
            else self._policy_path.with_name("metrics_verify_policy_registry_audit.jsonl")
        )
        self._policy: dict[str, int] = dict(DEFAULT_POLICY)
        self._updated_at = now_utc()
        self._audit_entries: list[dict[str, object]] = []
        self._rollback_approvals: list[dict[str, object]] = []
        self._rollback_approval_purge_audits: list[dict[str, object]] = []
        self._verify_policy_registry: dict[str, object] = dict(DEFAULT_VERIFY_POLICY_REGISTRY)
        self._verify_policy_registry_updated_at = now_utc()
        self._verify_policy_registry_audits: list[dict[str, object]] = []
        self._rollback_approval_ttl_seconds = max(1, int(rollback_approval_ttl_seconds))
        self._load_policy()
        self._load_audits()
        self._load_rollback_approvals()
        self._load_rollback_approval_purge_audits()
        self._load_verify_policy_registry()
        self._load_verify_policy_registry_audits()

    def get_policy(self) -> dict[str, object]:
        payload: dict[str, object] = dict(self._policy)
        payload["policy_path"] = str(self._policy_path)
        payload["updated_at"] = self._updated_at
        payload["audit_count"] = len(self._audit_entries)
        return payload

    def get_verify_policy_registry(self) -> dict[str, object]:
        payload = self._serialize_verify_policy_registry(dict(self._verify_policy_registry))
        payload["registry_path"] = str(self._verify_policy_registry_path)
        payload["updated_at"] = self._verify_policy_registry_updated_at
        payload["audit_count"] = len(self._verify_policy_registry_audits)
        return payload

    def export_verify_policy_registry(self) -> dict[str, object]:
        payload = self._serialize_verify_policy_registry(dict(self._verify_policy_registry))
        payload["generated_at"] = now_utc()
        payload["source"] = "metrics_verify_policy_registry"
        return payload

    def update_verify_policy_registry(
        self,
        registry: dict[str, object],
        *,
        updated_by: str,
        reason: str | None = None,
    ) -> dict[str, object]:
        normalized = self._normalize_verify_policy_registry(registry)
        self._verify_policy_registry = normalized
        self._verify_policy_registry_updated_at = now_utc()
        self._verify_policy_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._verify_policy_registry_path.write_text(
            json.dumps(
                self._serialize_verify_policy_registry(dict(normalized)),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        entry = {
            "id": new_id("vpr"),
            "updated_at": self._verify_policy_registry_updated_at,
            "updated_by": updated_by.strip(),
            "reason": reason,
            "registry": self._serialize_verify_policy_registry(dict(normalized)),
        }
        self._verify_policy_registry_audits.append(entry)
        self._append_verify_policy_registry_audit(entry)
        return self.get_verify_policy_registry()

    def list_verify_policy_registry_audits(
        self,
        *,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        if limit < 1:
            return []
        return list(reversed(self._verify_policy_registry_audits[-limit:]))

    def update_policy(
        self,
        policy: dict[str, int],
        *,
        updated_by: str,
        reason: str | None = None,
    ) -> dict[str, object]:
        normalized = self._normalize_policy(policy)
        self._policy = normalized
        self._updated_at = now_utc()
        self._policy_path.parent.mkdir(parents=True, exist_ok=True)
        self._policy_path.write_text(
            json.dumps(self._policy, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        entry = {
            "id": new_id("map"),
            "updated_at": self._updated_at,
            "updated_by": updated_by.strip(),
            "reason": reason,
            "policy": dict(self._policy),
        }
        self._audit_entries.append(entry)
        self._append_audit(entry)
        return self.get_policy()

    def list_audits(self, *, limit: int = 20) -> list[dict[str, object]]:
        if limit < 1:
            return []
        return list(reversed(self._audit_entries[-limit:]))

    def rollback_to_audit(
        self,
        audit_id: str,
        *,
        updated_by: str,
        reason: str | None = None,
        dry_run: bool = False,
        idempotency_key: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, object]:
        target = self.get_audit(audit_id)
        if target is None:
            raise KeyError(f"audit not found: {audit_id}")

        payload = target.get("policy")
        if not isinstance(payload, dict):
            raise ValueError(f"audit has no policy payload: {audit_id}")
        normalized = self._normalize_policy(payload)
        request_id = (idempotency_key or "").strip()

        if request_id:
            replay = self._find_rollback_by_request_id(request_id)
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
                    "policy": self._normalize_policy(replay_policy),
                    "policy_path": str(self._policy_path),
                    "audit_count": len(self._audit_entries),
                }

        if normalized == self._policy:
            if dry_run:
                return {
                    "source_audit_id": audit_id,
                    "dry_run": True,
                    "applied": False,
                    "idempotent_replay": False,
                    "policy": normalized,
                    "policy_path": str(self._policy_path),
                    "audit_count": len(self._audit_entries),
                }
            raise PolicyRollbackConflictError("policy already matches rollback target")

        if dry_run:
            return {
                "source_audit_id": audit_id,
                "dry_run": True,
                "applied": False,
                "idempotent_replay": False,
                "policy": normalized,
                "policy_path": str(self._policy_path),
                "audit_count": len(self._audit_entries),
            }

        if approval_id is not None:
            normalized_approval_id = approval_id.strip()
            if not normalized_approval_id:
                raise PolicyRollbackApprovalError("rollback approval id is empty")
            self.consume_rollback_approval(
                normalized_approval_id,
                audit_id=audit_id,
                used_by=updated_by.strip(),
            )
        else:
            normalized_approval_id = None

        self._policy = normalized
        self._updated_at = now_utc()
        self._policy_path.parent.mkdir(parents=True, exist_ok=True)
        self._policy_path.write_text(
            json.dumps(self._policy, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        entry = {
            "id": new_id("map"),
            "updated_at": self._updated_at,
            "updated_by": updated_by.strip(),
            "reason": reason,
            "rollback_from_audit_id": audit_id,
            "rollback_request_id": request_id or None,
            "rollback_approval_id": normalized_approval_id,
            "policy": dict(self._policy),
        }
        self._audit_entries.append(entry)
        self._append_audit(entry)
        return {
            "source_audit_id": audit_id,
            "dry_run": False,
            "applied": True,
            "idempotent_replay": False,
            "policy": dict(self._policy),
            "policy_path": str(self._policy_path),
            "audit_count": len(self._audit_entries),
        }

    def get_audit(self, audit_id: str) -> dict[str, object] | None:
        for entry in reversed(self._audit_entries):
            if str(entry.get("id", "")).strip() == audit_id:
                return dict(entry)
        return None

    def create_rollback_approval(
        self,
        *,
        audit_id: str,
        requested_by: str,
        reason: str | None = None,
    ) -> dict[str, object]:
        if self.get_audit(audit_id) is None:
            raise KeyError(f"audit not found: {audit_id}")
        now = now_utc()
        expires_at = now + timedelta(seconds=self._rollback_approval_ttl_seconds)
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
        self._rollback_approvals.append(entry)
        self._persist_rollback_approvals()
        return dict(entry)

    def approve_rollback_approval(
        self,
        approval_id: str,
        *,
        approved_by: str,
    ) -> dict[str, object]:
        self._refresh_rollback_approval_statuses()
        approval = self._find_rollback_approval(approval_id)
        if approval is None:
            raise KeyError(f"rollback approval not found: {approval_id}")
        status = str(approval.get("status", "")).strip()
        if status == "approved":
            return dict(approval)
        if status == "expired":
            raise PolicyRollbackApprovalError(
                f"rollback approval expired: {approval_id}"
            )
        if status != "pending":
            raise PolicyRollbackApprovalError(
                f"rollback approval is not pending: {approval_id}"
            )

        approval["status"] = "approved"
        approval["approved_by"] = approved_by.strip()
        approval["updated_at"] = now_utc()
        self._persist_rollback_approvals()
        return dict(approval)

    def consume_rollback_approval(
        self,
        approval_id: str,
        *,
        audit_id: str,
        used_by: str,
    ) -> dict[str, object]:
        self._refresh_rollback_approval_statuses()
        approval = self._find_rollback_approval(approval_id)
        if approval is None:
            raise KeyError(f"rollback approval not found: {approval_id}")

        request_audit_id = str(approval.get("audit_id", "")).strip()
        if request_audit_id != audit_id:
            raise PolicyRollbackApprovalError(
                "rollback approval is bound to another audit id"
            )

        status = str(approval.get("status", "")).strip()
        if status == "used":
            raise PolicyRollbackConflictError(
                f"rollback approval already used: {approval_id}"
            )
        if status == "expired":
            raise PolicyRollbackApprovalError(
                f"rollback approval expired: {approval_id}"
            )
        if status != "approved":
            raise PolicyRollbackApprovalError(
                f"rollback approval is not approved: {approval_id}"
            )

        approval["status"] = "used"
        approval["used_by"] = used_by.strip()
        approval["updated_at"] = now_utc()
        self._persist_rollback_approvals()
        return dict(approval)

    def list_rollback_approvals(
        self,
        *,
        limit: int = 20,
        status: str | None = None,
    ) -> list[dict[str, object]]:
        self._refresh_rollback_approval_statuses()
        if limit < 1:
            return []
        records = self._rollback_approvals
        if status is not None:
            normalized_status = status.strip().lower()
            records = [
                item
                for item in records
                if str(item.get("status", "")).strip().lower() == normalized_status
            ]
        return list(reversed(records[-limit:]))

    def get_rollback_approval_stats(self) -> dict[str, int]:
        self._refresh_rollback_approval_statuses()
        counts: dict[str, int] = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "used": 0,
            "expired": 0,
        }
        for entry in self._rollback_approvals:
            status = str(entry.get("status", "")).strip().lower()
            if status in counts:
                counts[status] += 1
        return {
            "total": len(self._rollback_approvals),
            "pending": counts["pending"],
            "approved": counts["approved"],
            "rejected": counts["rejected"],
            "used": counts["used"],
            "expired": counts["expired"],
        }

    def purge_rollback_approvals(
        self,
        *,
        remove_used: bool = True,
        remove_expired: bool = True,
        dry_run: bool = False,
        older_than_seconds: int | None = None,
        requested_by: str | None = None,
    ) -> dict[str, object]:
        self._refresh_rollback_approval_statuses(persist=not dry_run)
        keep: list[dict[str, object]] = []
        removed_used = 0
        removed_expired = 0
        if older_than_seconds is not None:
            retention_seconds = max(0, int(older_than_seconds))
            now = now_utc()
        else:
            retention_seconds = None
            now = None
        for entry in self._rollback_approvals:
            status = str(entry.get("status", "")).strip()
            if retention_seconds is not None:
                if not self._is_older_than(
                    entry,
                    seconds=retention_seconds,
                    now=now,
                ):
                    keep.append(entry)
                    continue
            if status == "used" and remove_used:
                removed_used += 1
                continue
            if status == "expired" and remove_expired:
                removed_expired += 1
                continue
            keep.append(entry)

        if not dry_run:
            self._rollback_approvals = keep
            if removed_used or removed_expired:
                self._persist_rollback_approvals()

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
            self._rollback_approval_purge_audits.append(audit_entry)
            self._append_rollback_approval_purge_audit(audit_entry)
            result["purge_audit_id"] = str(audit_entry["id"])
        return result

    def list_rollback_approval_purge_audits(
        self,
        *,
        limit: int = 20,
        event_type: str | None = None,
        created_after=None,
        created_before=None,
    ) -> list[dict[str, object]]:
        if limit < 1:
            return []
        records = self._rollback_approval_purge_audits
        normalized_event_type = (event_type or "").strip().lower()
        if normalized_event_type:
            records = [
                item
                for item in records
                if str(item.get("event_type", "")).strip().lower()
                == normalized_event_type
            ]
        if created_after is not None:
            records = [
                item
                for item in records
                if self._is_timestamp_after(item.get("created_at"), created_after)
            ]
        if created_before is not None:
            records = [
                item
                for item in records
                if self._is_timestamp_before(item.get("created_at"), created_before)
            ]
        return list(reversed(records[-limit:]))

    def purge_rollback_approval_purge_audits(
        self,
        *,
        dry_run: bool = False,
        older_than_seconds: int | None = None,
        keep_latest: int = 0,
        requested_by: str | None = None,
    ) -> dict[str, object]:
        entries = self._rollback_approval_purge_audits
        latest_to_keep = max(0, int(keep_latest))
        protected_ids: set[str] = set()
        if latest_to_keep > 0 and entries:
            for entry in entries[-latest_to_keep:]:
                entry_id = str(entry.get("id", "")).strip()
                if entry_id:
                    protected_ids.add(entry_id)
        if older_than_seconds is not None:
            retention_seconds = max(0, int(older_than_seconds))
            now = now_utc()
        else:
            retention_seconds = None
            now = None

        keep: list[dict[str, object]] = []
        removed_total = 0
        for entry in entries:
            entry_id = str(entry.get("id", "")).strip()
            if entry_id and entry_id in protected_ids:
                keep.append(entry)
                continue
            if retention_seconds is not None and not self._is_older_than(
                entry,
                seconds=retention_seconds,
                now=now,
            ):
                keep.append(entry)
                continue
            removed_total += 1

        if not dry_run:
            self._rollback_approval_purge_audits = keep
            if removed_total:
                self._persist_rollback_approval_purge_audits()

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
            self._rollback_approval_purge_audits.append(audit_entry)
            self._append_rollback_approval_purge_audit(audit_entry)
            result["purge_audit_gc_id"] = str(audit_entry["id"])
        return result

    @staticmethod
    def _is_older_than(
        entry: dict[str, object],
        *,
        seconds: int,
        now,
    ) -> bool:
        if seconds <= 0:
            return True
        timestamp = entry.get("updated_at") or entry.get("created_at")
        if timestamp is None or not hasattr(timestamp, "tzinfo"):
            return False
        delta = now - timestamp
        return delta.total_seconds() >= seconds

    @staticmethod
    def _is_timestamp_after(timestamp, threshold) -> bool:
        if timestamp is None or threshold is None:
            return False
        if not hasattr(timestamp, "tzinfo") or not hasattr(threshold, "tzinfo"):
            return False
        return timestamp >= threshold

    @staticmethod
    def _is_timestamp_before(timestamp, threshold) -> bool:
        if timestamp is None or threshold is None:
            return False
        if not hasattr(timestamp, "tzinfo") or not hasattr(threshold, "tzinfo"):
            return False
        return timestamp <= threshold

    def _find_rollback_by_request_id(self, request_id: str) -> dict[str, object] | None:
        for entry in reversed(self._audit_entries):
            rollback_request_id = str(entry.get("rollback_request_id", "")).strip()
            if rollback_request_id == request_id:
                return dict(entry)
        return None

    def _refresh_rollback_approval_statuses(self, *, persist: bool = True) -> int:
        now = now_utc()
        changed = 0
        for entry in self._rollback_approvals:
            status = str(entry.get("status", "")).strip().lower()
            if status not in {"pending", "approved"}:
                continue
            expires_at = entry.get("expires_at")
            if not hasattr(expires_at, "tzinfo"):
                continue
            if expires_at <= now:
                entry["status"] = "expired"
                entry["updated_at"] = now
                changed += 1
        if changed and persist:
            self._persist_rollback_approvals()
        return changed

    def _find_rollback_approval(self, approval_id: str) -> dict[str, object] | None:
        for entry in self._rollback_approvals:
            if str(entry.get("id", "")).strip() == approval_id:
                return entry
        return None

    def _load_rollback_approvals(self) -> None:
        if not self._rollback_approval_path.exists():
            return
        try:
            approvals: list[dict[str, object]] = []
            for line in self._rollback_approval_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    continue
                if "id" not in payload or "audit_id" not in payload:
                    continue
                approvals.append(self._deserialize_audit(payload))
            self._rollback_approvals = approvals
        except Exception:  # noqa: BLE001
            self._rollback_approvals = []

    def _persist_rollback_approvals(self) -> None:
        self._rollback_approval_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for entry in self._rollback_approvals:
            serializable = dict(entry)
            for key in ("created_at", "updated_at", "expires_at"):
                value = serializable.get(key)
                if value is not None and hasattr(value, "isoformat"):
                    serializable[key] = value.isoformat()
            lines.append(json.dumps(serializable, ensure_ascii=False))
        payload = "\n".join(lines) + ("\n" if lines else "")
        self._rollback_approval_path.write_text(payload, encoding="utf-8")

    def _load_rollback_approval_purge_audits(self) -> None:
        if not self._rollback_approval_purge_audit_path.exists():
            return
        try:
            entries: list[dict[str, object]] = []
            for line in self._rollback_approval_purge_audit_path.read_text(
                encoding="utf-8"
            ).splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    continue
                if "id" not in payload:
                    continue
                entries.append(self._deserialize_audit(payload))
            self._rollback_approval_purge_audits = entries
        except Exception:  # noqa: BLE001
            self._rollback_approval_purge_audits = []

    def _append_rollback_approval_purge_audit(self, entry: dict[str, object]) -> None:
        self._rollback_approval_purge_audit_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = dict(entry)
        created_at = serializable.get("created_at")
        if created_at is not None and hasattr(created_at, "isoformat"):
            serializable["created_at"] = created_at.isoformat()
        with self._rollback_approval_purge_audit_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(serializable, ensure_ascii=False) + "\n")

    def _persist_rollback_approval_purge_audits(self) -> None:
        self._rollback_approval_purge_audit_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for entry in self._rollback_approval_purge_audits:
            serializable = dict(entry)
            created_at = serializable.get("created_at")
            if created_at is not None and hasattr(created_at, "isoformat"):
                serializable["created_at"] = created_at.isoformat()
            lines.append(json.dumps(serializable, ensure_ascii=False))
        payload = "\n".join(lines) + ("\n" if lines else "")
        self._rollback_approval_purge_audit_path.write_text(payload, encoding="utf-8")

    def _load_verify_policy_registry(self) -> None:
        if not self._verify_policy_registry_path.exists():
            self._persist_default_verify_policy_registry()
            return
        try:
            payload = json.loads(self._verify_policy_registry_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                self._persist_default_verify_policy_registry()
                return
            self._verify_policy_registry = self._normalize_verify_policy_registry(payload)
            self._verify_policy_registry_updated_at = now_utc()
        except Exception:  # noqa: BLE001
            self._persist_default_verify_policy_registry()

    def _persist_default_verify_policy_registry(self) -> None:
        self._verify_policy_registry = self._normalize_verify_policy_registry(
            dict(DEFAULT_VERIFY_POLICY_REGISTRY)
        )
        self._verify_policy_registry_updated_at = now_utc()
        self._verify_policy_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._verify_policy_registry_path.write_text(
            json.dumps(
                self._serialize_verify_policy_registry(
                    dict(self._verify_policy_registry)
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _load_verify_policy_registry_audits(self) -> None:
        if not self._verify_policy_registry_audit_path.exists():
            return
        try:
            entries: list[dict[str, object]] = []
            for line in self._verify_policy_registry_audit_path.read_text(
                encoding="utf-8"
            ).splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    continue
                if "id" not in payload:
                    continue
                entries.append(self._deserialize_audit(payload))
            self._verify_policy_registry_audits = entries
        except Exception:  # noqa: BLE001
            self._verify_policy_registry_audits = []

    def _append_verify_policy_registry_audit(self, entry: dict[str, object]) -> None:
        self._verify_policy_registry_audit_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = dict(entry)
        updated_at = serializable.get("updated_at")
        if updated_at is not None and hasattr(updated_at, "isoformat"):
            serializable["updated_at"] = updated_at.isoformat()
        with self._verify_policy_registry_audit_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(serializable, ensure_ascii=False) + "\n")

    @staticmethod
    def _serialize_verify_policy_registry(payload: dict[str, object]) -> dict[str, object]:
        profiles_payload = payload.get("profiles")
        serialized_profiles: dict[str, dict[str, object]] = {}
        if isinstance(profiles_payload, dict):
            for key, value in profiles_payload.items():
                profile_name = str(key).strip().lower()
                if not profile_name or not isinstance(value, dict):
                    continue
                profile_entry: dict[str, object] = {}
                allowed_resolvers = value.get("allowed_resolvers")
                if isinstance(allowed_resolvers, set):
                    profile_entry["allowed_resolvers"] = sorted(
                        str(item).strip()
                        for item in allowed_resolvers
                        if str(item).strip()
                    )
                elif isinstance(allowed_resolvers, list):
                    profile_entry["allowed_resolvers"] = sorted(
                        {
                            str(item).strip()
                            for item in allowed_resolvers
                            if str(item).strip()
                        }
                    )
                for field in (
                    "preflight_slo_min_pass_rate",
                    "preflight_slo_max_consecutive_failures",
                    "verify_slo_min_pass_rate",
                    "verify_slo_max_fetch_failures",
                ):
                    if field in value and value[field] is not None:
                        profile_entry[field] = value[field]
                serialized_profiles[profile_name] = profile_entry
        return {
            "default_profile": str(payload.get("default_profile", "")).strip().lower(),
            "profiles": serialized_profiles,
        }

    def _normalize_verify_policy_registry(self, payload: dict[str, object]) -> dict[str, object]:
        default_profile = str(payload.get("default_profile", "")).strip().lower()
        profiles_payload = payload.get("profiles", {})
        if profiles_payload is None:
            profiles_payload = {}
        if not isinstance(profiles_payload, dict):
            raise ValueError("verify policy registry profiles must be object")
        normalized_profiles: dict[str, dict[str, object]] = {}
        for key, value in profiles_payload.items():
            profile_name = str(key).strip().lower()
            if not profile_name:
                continue
            if not isinstance(value, dict):
                raise ValueError(f"invalid verify policy profile: {profile_name}")
            profile_entry: dict[str, object] = {}
            if "allowed_resolvers" in value:
                allowed_value = value.get("allowed_resolvers")
                if not isinstance(allowed_value, list):
                    raise ValueError(
                        f"invalid allowed_resolvers in verify policy profile: {profile_name}"
                    )
                allowed_resolvers = {
                    str(item).strip()
                    for item in allowed_value
                    if str(item).strip()
                }
                invalid_resolvers = sorted(
                    allowed_resolvers - VERIFY_POLICY_ALLOWED_RESOLVERS
                )
                if invalid_resolvers:
                    raise ValueError(
                        "invalid allowed_resolvers in verify policy profile: "
                        + ",".join(invalid_resolvers)
                    )
                profile_entry["allowed_resolvers"] = allowed_resolvers
            for field in (
                "preflight_slo_min_pass_rate",
                "verify_slo_min_pass_rate",
            ):
                if field not in value or value[field] is None:
                    continue
                raw_value = value[field]
                if not isinstance(raw_value, (int, float)):
                    raise ValueError(f"invalid {field} in verify policy profile: {profile_name}")
                float_value = float(raw_value)
                if not (0.0 <= float_value <= 1.0):
                    raise ValueError(
                        f"invalid {field} in verify policy profile: {profile_name}"
                    )
                profile_entry[field] = float_value
            for field in (
                "preflight_slo_max_consecutive_failures",
                "verify_slo_max_fetch_failures",
            ):
                if field not in value or value[field] is None:
                    continue
                raw_value = value[field]
                if not isinstance(raw_value, (int, float)):
                    raise ValueError(f"invalid {field} in verify policy profile: {profile_name}")
                int_value = int(raw_value)
                if int_value < 0:
                    raise ValueError(
                        f"invalid {field} in verify policy profile: {profile_name}"
                    )
                profile_entry[field] = int_value
            normalized_profiles[profile_name] = profile_entry
        return {
            "default_profile": default_profile,
            "profiles": normalized_profiles,
        }

    def _load_policy(self) -> None:
        if not self._policy_path.exists():
            self._persist_default_policy()
            return

        try:
            payload = json.loads(self._policy_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                self._persist_default_policy()
                return
            self._policy = self._normalize_policy(payload)
            self._updated_at = now_utc()
        except Exception:  # noqa: BLE001
            self._persist_default_policy()

    def _persist_default_policy(self) -> None:
        self._policy = dict(DEFAULT_POLICY)
        self._updated_at = now_utc()
        self._policy_path.parent.mkdir(parents=True, exist_ok=True)
        self._policy_path.write_text(
            json.dumps(self._policy, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _normalize_policy(self, payload: dict[str, object]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for key, default_value in DEFAULT_POLICY.items():
            raw = payload.get(key, default_value)
            value = default_value
            if isinstance(raw, (int, float)):
                value = int(raw)
            elif isinstance(raw, str):
                cleaned = raw.strip()
                if cleaned:
                    try:
                        value = int(cleaned)
                    except ValueError:
                        value = default_value
            if value < 0:
                value = 0
            normalized[key] = value
        return normalized

    def _load_audits(self) -> None:
        if not self._audit_path.exists():
            return
        try:
            for line in self._audit_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    continue
                if "id" not in payload:
                    continue
                self._audit_entries.append(self._deserialize_audit(payload))
        except Exception:  # noqa: BLE001
            self._audit_entries = []

    def _append_audit(self, entry: dict[str, object]) -> None:
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = dict(entry)
        updated_at = serializable.get("updated_at")
        if updated_at is not None and hasattr(updated_at, "isoformat"):
            serializable["updated_at"] = updated_at.isoformat()
        with self._audit_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(serializable, ensure_ascii=False) + "\n")

    @staticmethod
    def _deserialize_audit(payload: dict[str, object]) -> dict[str, object]:
        entry = dict(payload)
        for key in ("created_at", "updated_at", "expires_at"):
            timestamp = entry.get(key)
            if isinstance(timestamp, str):
                try:
                    from datetime import datetime

                    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    entry[key] = parsed
                except Exception:  # noqa: BLE001
                    pass
        return entry
