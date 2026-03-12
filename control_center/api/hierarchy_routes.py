from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, status

from control_center.models import (
    ApproveCommandRequest,
    Command,
    CommandAcceptedResponse,
    CreateCommandRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    Project,
    ProjectDetail,
    Task,
)
from control_center.services import InMemoryOrchestrator


def create_hierarchy_router(
    *,
    store: InMemoryOrchestrator | None = None,
    store_provider: Callable[[], InMemoryOrchestrator] | None = None,
) -> APIRouter:
    if store is None and store_provider is None:
        raise ValueError("store is required for hierarchy router initialization")

    def _store() -> InMemoryOrchestrator:
        if store_provider is not None:
            return store_provider()
        assert store is not None
        return store

    router = APIRouter()

    @router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
    async def create_project(payload: CreateProjectRequest) -> Project:
        return await _store().create_project(payload)

    @router.get("/projects", response_model=list[Project])
    async def list_projects() -> list[Project]:
        return await _store().list_projects()

    @router.post(
        "/projects/{project_id}/tasks",
        response_model=Task,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_task(project_id: str, payload: CreateTaskRequest) -> Task:
        return await _store().create_task(project_id, payload)

    @router.get("/projects/{project_id}/tasks", response_model=list[Task])
    async def list_tasks(project_id: str) -> list[Task]:
        return await _store().list_tasks(project_id)

    @router.get("/tasks/{task_id}", response_model=Task)
    async def get_task(task_id: str) -> Task:
        return await _store().get_task(task_id)

    @router.post(
        "/tasks/{task_id}/commands",
        response_model=CommandAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def create_command(
        task_id: str,
        payload: CreateCommandRequest,
    ) -> CommandAcceptedResponse:
        command = await _store().create_command(task_id, payload)
        return CommandAcceptedResponse(
            command_id=command.id,
            task_id=command.task_id,
            project_id=command.project_id,
            status=command.status,
            poll_url=f"/commands/{command.id}",
        )

    @router.get("/tasks/{task_id}/commands", response_model=list[Command])
    async def list_commands(task_id: str) -> list[Command]:
        return await _store().list_commands(task_id)

    @router.get("/commands/{command_id}", response_model=Command)
    async def get_command(command_id: str) -> Command:
        return await _store().get_command(command_id)

    @router.post("/commands/{command_id}/approve", response_model=Command)
    async def approve_command(command_id: str, payload: ApproveCommandRequest) -> Command:
        return await _store().approve_command(command_id, payload.approved_by)

    @router.get("/projects/{project_id}/snapshot", response_model=ProjectDetail)
    async def get_project_snapshot(project_id: str) -> ProjectDetail:
        return await _store().get_project_detail(project_id)

    return router
