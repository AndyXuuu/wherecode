from __future__ import annotations

from pathlib import Path

import pytest

from control_center.services.context_memory_store import ContextMemoryStore
from control_center.services.sqlite_state_store import SQLiteStateStore


def test_context_memory_upsert_get_and_version_increment() -> None:
    store = ContextMemoryStore()

    first = store.upsert(
        scope="shared",
        key="risk_level",
        value="low",
        updated_by="chief-architect",
    )
    second = store.upsert(
        scope="shared",
        key="risk_level",
        value="medium",
        updated_by="chief-architect",
    )

    assert first["version"] == 1
    assert second["version"] == 2
    loaded = store.get(scope="shared", key="risk_level")
    assert loaded is not None
    assert loaded["value"] == "medium"


def test_context_memory_namespace_validation() -> None:
    store = ContextMemoryStore()
    with pytest.raises(ValueError):
        store.upsert(
            scope="shared",
            key="k",
            value=1,
            updated_by="ops",
            project_id="p1",
        )

    with pytest.raises(ValueError):
        store.upsert(
            scope="project",
            key="k",
            value=1,
            updated_by="ops",
        )

    with pytest.raises(ValueError):
        store.upsert(
            scope="run",
            key="k",
            value=1,
            updated_by="ops",
        )


def test_context_memory_resolve_priority_run_over_project_over_shared() -> None:
    store = ContextMemoryStore()
    store.upsert(scope="shared", key="lang", value="python", updated_by="chief")
    store.upsert(
        scope="project",
        project_id="p1",
        key="lang",
        value="go",
        updated_by="backend-dev",
    )
    store.upsert(
        scope="run",
        project_id="p1",
        run_id="r1",
        key="lang",
        value="rust",
        updated_by="backend-dev",
    )

    resolved = store.resolve(project_id="p1", run_id="r1")
    assert resolved["values"]["lang"] == "rust"
    assert resolved["source_namespaces"]["lang"] == "run:r1"
    assert resolved["scope_chain"] == ["shared", "project:p1", "run:r1"]


def test_context_memory_delete_persists_tombstone_for_reload(tmp_path: Path) -> None:
    state_store = SQLiteStateStore(str(tmp_path / "state.db"))
    store = ContextMemoryStore(state_store=state_store)
    store.upsert(
        scope="project",
        project_id="p1",
        key="budget",
        value=3,
        updated_by="ops",
    )
    deleted, _deleted_at = store.delete(
        scope="project",
        project_id="p1",
        key="budget",
        deleted_by="ops",
    )
    assert deleted is True
    assert store.get(scope="project", project_id="p1", key="budget") is None

    reloaded = ContextMemoryStore(state_store=state_store)
    assert reloaded.get(scope="project", project_id="p1", key="budget") is None
