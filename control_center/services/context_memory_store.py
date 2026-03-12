from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

from control_center.models.api_context_memory import MemoryNamespaceScope
from control_center.models.hierarchy import now_utc
from control_center.services.sqlite_state_store import SQLiteStateStore


class ContextMemoryStore:
    ENTITY_TYPE = "context_memory_item"

    def __init__(
        self,
        *,
        state_store: SQLiteStateStore | None = None,
        now_utc_handler: Callable[[], datetime] = now_utc,
    ) -> None:
        self._state_store = state_store
        self._now_utc = now_utc_handler
        self._items_by_namespace: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
        self._load_state()

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _resolve_namespace(
        self,
        *,
        scope: MemoryNamespaceScope,
        project_id: str | None,
        run_id: str | None,
    ) -> tuple[str, str | None, str | None]:
        normalized_project_id = self._normalize_optional(project_id)
        normalized_run_id = self._normalize_optional(run_id)

        if scope == "shared":
            if normalized_project_id or normalized_run_id:
                raise ValueError("shared scope does not accept project_id or run_id")
            return "shared", None, None

        if scope == "project":
            if not normalized_project_id:
                raise ValueError("project scope requires project_id")
            if normalized_run_id:
                raise ValueError("project scope does not accept run_id")
            return f"project:{normalized_project_id}", normalized_project_id, None

        if not normalized_run_id:
            raise ValueError("run scope requires run_id")
        return f"run:{normalized_run_id}", normalized_project_id, normalized_run_id

    def resolve_namespace_id(
        self,
        *,
        scope: MemoryNamespaceScope,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        namespace_id, _project_id, _run_id = self._resolve_namespace(
            scope=scope,
            project_id=project_id,
            run_id=run_id,
        )
        return namespace_id

    @staticmethod
    def _normalize_key(key: str) -> str:
        normalized = key.strip()
        if not normalized:
            raise ValueError("memory key must be non-empty")
        return normalized

    @staticmethod
    def _normalize_actor(updated_by: str) -> str:
        normalized = updated_by.strip()
        if not normalized:
            raise ValueError("updated_by must be non-empty")
        return normalized

    def _state_entity_id(self, namespace_id: str, key: str) -> str:
        return f"{namespace_id}::{key}"

    def _persist(self, payload: dict[str, object]) -> None:
        if self._state_store is None:
            return
        namespace_id = str(payload.get("namespace_id", "")).strip()
        key = str(payload.get("key", "")).strip()
        self._state_store.upsert(
            self.ENTITY_TYPE,
            self._state_entity_id(namespace_id, key),
            payload,
        )

    def _load_state(self) -> None:
        if self._state_store is None:
            return
        for payload in self._state_store.list(self.ENTITY_TYPE):
            if not isinstance(payload, dict):
                continue
            if payload.get("deleted") is True:
                continue
            namespace_id = str(payload.get("namespace_id", "")).strip()
            key = str(payload.get("key", "")).strip()
            scope = str(payload.get("scope", "")).strip()
            if not namespace_id or not key:
                continue
            if scope not in {"shared", "project", "run"}:
                continue
            self._items_by_namespace[namespace_id][key] = dict(payload)

    def upsert(
        self,
        *,
        scope: MemoryNamespaceScope,
        key: str,
        value: object | None,
        updated_by: str,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, object]:
        namespace_id, normalized_project_id, normalized_run_id = self._resolve_namespace(
            scope=scope,
            project_id=project_id,
            run_id=run_id,
        )
        normalized_key = self._normalize_key(key)
        actor = self._normalize_actor(updated_by)
        now = self._now_utc()

        existing = self._items_by_namespace[namespace_id].get(normalized_key)
        if existing is None:
            created_at = now.isoformat()
            version = 1
        else:
            created_at = str(existing.get("created_at", now.isoformat()))
            try:
                version = int(existing.get("version", 1)) + 1
            except (TypeError, ValueError):
                version = 1

        record: dict[str, object] = {
            "scope": scope,
            "namespace_id": namespace_id,
            "key": normalized_key,
            "value": value,
            "project_id": normalized_project_id,
            "run_id": normalized_run_id,
            "created_at": created_at,
            "updated_at": now.isoformat(),
            "updated_by": actor,
            "version": version,
            "deleted": False,
        }
        self._items_by_namespace[namespace_id][normalized_key] = record
        self._persist(record)
        return dict(record)

    def get(
        self,
        *,
        scope: MemoryNamespaceScope,
        key: str,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, object] | None:
        namespace_id, _project_id, _run_id = self._resolve_namespace(
            scope=scope,
            project_id=project_id,
            run_id=run_id,
        )
        normalized_key = self._normalize_key(key)
        item = self._items_by_namespace.get(namespace_id, {}).get(normalized_key)
        return dict(item) if item is not None else None

    def delete(
        self,
        *,
        scope: MemoryNamespaceScope,
        key: str,
        project_id: str | None = None,
        run_id: str | None = None,
        deleted_by: str = "system",
    ) -> tuple[bool, str]:
        namespace_id, normalized_project_id, normalized_run_id = self._resolve_namespace(
            scope=scope,
            project_id=project_id,
            run_id=run_id,
        )
        normalized_key = self._normalize_key(key)
        actor = self._normalize_actor(deleted_by)
        now = self._now_utc().isoformat()
        deleted = normalized_key in self._items_by_namespace.get(namespace_id, {})
        self._items_by_namespace.get(namespace_id, {}).pop(normalized_key, None)
        tombstone = {
            "scope": scope,
            "namespace_id": namespace_id,
            "key": normalized_key,
            "project_id": normalized_project_id,
            "run_id": normalized_run_id,
            "updated_at": now,
            "updated_by": actor,
            "deleted": True,
        }
        self._persist(tombstone)
        return deleted, now

    def list_namespace(
        self,
        *,
        scope: MemoryNamespaceScope,
        project_id: str | None = None,
        run_id: str | None = None,
        prefix: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        namespace_id, _project_id, _run_id = self._resolve_namespace(
            scope=scope,
            project_id=project_id,
            run_id=run_id,
        )
        if limit < 1:
            return []
        records = list(self._items_by_namespace.get(namespace_id, {}).values())
        normalized_prefix = (prefix or "").strip()
        if normalized_prefix:
            records = [
                item
                for item in records
                if str(item.get("key", "")).startswith(normalized_prefix)
            ]
        records.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return [dict(item) for item in records[:limit]]

    def resolve(
        self,
        *,
        project_id: str | None = None,
        run_id: str | None = None,
        keys: list[str] | None = None,
    ) -> dict[str, object]:
        normalized_project_id = self._normalize_optional(project_id)
        normalized_run_id = self._normalize_optional(run_id)
        scope_chain = ["shared"]
        if normalized_project_id:
            scope_chain.append(f"project:{normalized_project_id}")
        if normalized_run_id:
            scope_chain.append(f"run:{normalized_run_id}")

        selected_keys: set[str] | None = None
        if keys is not None:
            cleaned = {self._normalize_key(key) for key in keys if key is not None}
            selected_keys = cleaned if cleaned else set()

        values: dict[str, object | None] = {}
        source_namespaces: dict[str, str] = {}
        for namespace_id in scope_chain:
            for key, item in self._items_by_namespace.get(namespace_id, {}).items():
                if selected_keys is not None and key not in selected_keys:
                    continue
                values[key] = item.get("value")
                source_namespaces[key] = namespace_id

        return {
            "scope_chain": scope_chain,
            "values": values,
            "source_namespaces": source_namespaces,
            "resolved_at": self._now_utc(),
        }
