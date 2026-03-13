from __future__ import annotations

import json
from pathlib import Path

from control_center.models.hierarchy import new_id, now_utc
from control_center.services.metrics_alert_policy_store_mutations import (
    approve_rollback_approval as approve_rollback_approval_impl,
    consume_rollback_approval as consume_rollback_approval_impl,
    create_rollback_approval as create_rollback_approval_impl,
    get_rollback_approval_stats as get_rollback_approval_stats_impl,
    list_rollback_approval_purge_audits as list_rollback_approval_purge_audits_impl,
    list_rollback_approvals as list_rollback_approvals_impl,
    purge_rollback_approval_purge_audits as purge_rollback_approval_purge_audits_impl,
    purge_rollback_approvals as purge_rollback_approvals_impl,
    rollback_to_audit as rollback_to_audit_impl,
)
from control_center.services.metrics_alert_policy_store_io import (
    append_audit_line,
    load_audits as load_audits_io,
    load_policy as load_policy_io,
    load_verify_policy_registry as load_verify_policy_registry_io,
    load_verify_policy_registry_audits as load_verify_policy_registry_audits_io,
    persist_default_policy as persist_default_policy_io,
    persist_default_verify_policy_registry as persist_default_verify_policy_registry_io,
)
from control_center.services.metrics_alert_policy_store_rollback import (
    append_rollback_approval_purge_audit,
    find_rollback_approval,
    is_older_than,
    is_timestamp_after,
    is_timestamp_before,
    load_rollback_approval_purge_audits,
    load_rollback_approvals,
    persist_rollback_approval_purge_audits,
    persist_rollback_approvals,
    refresh_rollback_approval_statuses,
)
from control_center.services.metrics_alert_policy_store_verify import (
    normalize_verify_policy_registry,
    serialize_verify_policy_registry,
)
from control_center.services.metrics_alert_policy_store_policy import (
    deserialize_audit_timestamps,
    find_rollback_by_request_id,
    normalize_policy,
)


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
        return rollback_to_audit_impl(
            self,
            audit_id,
            updated_by=updated_by,
            reason=reason,
            dry_run=dry_run,
            idempotency_key=idempotency_key,
            approval_id=approval_id,
        )

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
        return create_rollback_approval_impl(
            self,
            audit_id=audit_id,
            requested_by=requested_by,
            reason=reason,
        )

    def approve_rollback_approval(
        self,
        approval_id: str,
        *,
        approved_by: str,
    ) -> dict[str, object]:
        return approve_rollback_approval_impl(
            self,
            approval_id,
            approved_by=approved_by,
        )

    def consume_rollback_approval(
        self,
        approval_id: str,
        *,
        audit_id: str,
        used_by: str,
    ) -> dict[str, object]:
        return consume_rollback_approval_impl(
            self,
            approval_id,
            audit_id=audit_id,
            used_by=used_by,
        )

    def list_rollback_approvals(
        self,
        *,
        limit: int = 20,
        status: str | None = None,
    ) -> list[dict[str, object]]:
        return list_rollback_approvals_impl(self, limit=limit, status=status)

    def get_rollback_approval_stats(self) -> dict[str, int]:
        return get_rollback_approval_stats_impl(self)

    def purge_rollback_approvals(
        self,
        *,
        remove_used: bool = True,
        remove_expired: bool = True,
        dry_run: bool = False,
        older_than_seconds: int | None = None,
        requested_by: str | None = None,
    ) -> dict[str, object]:
        return purge_rollback_approvals_impl(
            self,
            remove_used=remove_used,
            remove_expired=remove_expired,
            dry_run=dry_run,
            older_than_seconds=older_than_seconds,
            requested_by=requested_by,
        )

    def list_rollback_approval_purge_audits(
        self,
        *,
        limit: int = 20,
        event_type: str | None = None,
        created_after=None,
        created_before=None,
    ) -> list[dict[str, object]]:
        return list_rollback_approval_purge_audits_impl(
            self,
            limit=limit,
            event_type=event_type,
            created_after=created_after,
            created_before=created_before,
        )

    def purge_rollback_approval_purge_audits(
        self,
        *,
        dry_run: bool = False,
        older_than_seconds: int | None = None,
        keep_latest: int = 0,
        requested_by: str | None = None,
    ) -> dict[str, object]:
        return purge_rollback_approval_purge_audits_impl(
            self,
            dry_run=dry_run,
            older_than_seconds=older_than_seconds,
            keep_latest=keep_latest,
            requested_by=requested_by,
        )

    @staticmethod
    def _is_older_than(
        entry: dict[str, object],
        *,
        seconds: int,
        now,
    ) -> bool:
        return is_older_than(entry, seconds=seconds, now=now)

    @staticmethod
    def _is_timestamp_after(timestamp, threshold) -> bool:
        return is_timestamp_after(timestamp, threshold)

    @staticmethod
    def _is_timestamp_before(timestamp, threshold) -> bool:
        return is_timestamp_before(timestamp, threshold)

    def _find_rollback_by_request_id(self, request_id: str) -> dict[str, object] | None:
        return find_rollback_by_request_id(self._audit_entries, request_id)

    def _refresh_rollback_approval_statuses(self, *, persist: bool = True) -> int:
        return refresh_rollback_approval_statuses(
            self._rollback_approvals,
            persist=persist,
            persist_handler=self._persist_rollback_approvals,
        )

    def _find_rollback_approval(self, approval_id: str) -> dict[str, object] | None:
        return find_rollback_approval(self._rollback_approvals, approval_id)

    def _load_rollback_approvals(self) -> None:
        self._rollback_approvals = load_rollback_approvals(
            self._rollback_approval_path,
            deserialize_audit=self._deserialize_audit,
        )

    def _persist_rollback_approvals(self) -> None:
        persist_rollback_approvals(
            self._rollback_approval_path,
            self._rollback_approvals,
        )

    def _load_rollback_approval_purge_audits(self) -> None:
        self._rollback_approval_purge_audits = load_rollback_approval_purge_audits(
            self._rollback_approval_purge_audit_path,
            deserialize_audit=self._deserialize_audit,
        )

    def _append_rollback_approval_purge_audit(self, entry: dict[str, object]) -> None:
        append_rollback_approval_purge_audit(
            self._rollback_approval_purge_audit_path,
            entry,
        )

    def _persist_rollback_approval_purge_audits(self) -> None:
        persist_rollback_approval_purge_audits(
            self._rollback_approval_purge_audit_path,
            self._rollback_approval_purge_audits,
        )

    def _load_verify_policy_registry(self) -> None:
        load_verify_policy_registry_io(self)

    def _persist_default_verify_policy_registry(self) -> None:
        persist_default_verify_policy_registry_io(
            self,
            default_verify_policy_registry=DEFAULT_VERIFY_POLICY_REGISTRY,
        )

    def _load_verify_policy_registry_audits(self) -> None:
        self._verify_policy_registry_audits = load_verify_policy_registry_audits_io(self)

    def _append_verify_policy_registry_audit(self, entry: dict[str, object]) -> None:
        append_audit_line(
            self._verify_policy_registry_audit_path,
            entry,
            timestamp_key="updated_at",
        )

    @staticmethod
    def _serialize_verify_policy_registry(payload: dict[str, object]) -> dict[str, object]:
        return serialize_verify_policy_registry(payload)

    def _normalize_verify_policy_registry(self, payload: dict[str, object]) -> dict[str, object]:
        return normalize_verify_policy_registry(
            payload,
            allowed_resolvers=VERIFY_POLICY_ALLOWED_RESOLVERS,
        )

    def _load_policy(self) -> None:
        load_policy_io(self)

    def _persist_default_policy(self) -> None:
        persist_default_policy_io(
            self,
            default_policy=DEFAULT_POLICY,
        )

    def _normalize_policy(self, payload: dict[str, object]) -> dict[str, int]:
        return normalize_policy(payload, defaults=DEFAULT_POLICY)

    def _load_audits(self) -> None:
        self._audit_entries = load_audits_io(self)

    def _append_audit(self, entry: dict[str, object]) -> None:
        append_audit_line(self._audit_path, entry, timestamp_key="updated_at")

    @staticmethod
    def _deserialize_audit(payload: dict[str, object]) -> dict[str, object]:
        return deserialize_audit_timestamps(payload)
