from __future__ import annotations

import asyncio
from pathlib import Path

from control_center.models import (
    CreateCommandRequest,
    CreateProjectRequest,
    CreateTaskRequest,
)
from control_center.services import InMemoryOrchestrator, SQLiteStateStore


def test_sqlite_state_store_upsert_list_clear(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))

    store.upsert("project", "proj_1", {"id": "proj_1", "name": "demo"})
    rows = store.list("project")
    assert len(rows) == 1
    assert rows[0]["id"] == "proj_1"

    store.clear()
    assert store.list("project") == []


def test_orchestrator_restores_state_from_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    state_store = SQLiteStateStore(str(db_path))

    orchestrator = InMemoryOrchestrator(state_store=state_store)
    project = asyncio.run(
        orchestrator.create_project(
            CreateProjectRequest(name="restore-project"),
        )
    )
    task = asyncio.run(
        orchestrator.create_task(
            project.id,
            CreateTaskRequest(title="restore-task"),
        )
    )
    accepted = asyncio.run(
        orchestrator.create_command(
            task.id,
            CreateCommandRequest(text="restore-command"),
        )
    )
    assert accepted.task_id == task.id

    restored = InMemoryOrchestrator(state_store=state_store)
    projects = asyncio.run(restored.list_projects())
    assert any(item.id == project.id for item in projects)

    tasks = asyncio.run(restored.list_tasks(project.id))
    assert any(item.id == task.id for item in tasks)

    commands = asyncio.run(restored.list_commands(task.id))
    assert any(item.id == accepted.id for item in commands)
