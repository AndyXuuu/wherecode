from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import timedelta

from fastapi import HTTPException

from control_center.models.hierarchy import (
    Command,
    CommandStatus,
    Project,
    ProjectDetail,
    Task,
    TaskDetail,
    TaskStatus,
    now_utc,
)
from control_center.models.api import (
    CreateCommandRequest,
    CreateProjectRequest,
    CreateTaskRequest,
)


class InMemoryOrchestrator:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._tasks: dict[str, Task] = {}
        self._commands: dict[str, Command] = {}
        self._project_tasks: dict[str, list[str]] = defaultdict(list)
        self._task_commands: dict[str, list[str]] = defaultdict(list)
        self._task_sequence: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        self._projects.clear()
        self._tasks.clear()
        self._commands.clear()
        self._project_tasks.clear()
        self._task_commands.clear()
        self._task_sequence.clear()

    async def create_project(self, payload: CreateProjectRequest) -> Project:
        async with self._lock:
            project = Project(
                name=payload.name,
                description=payload.description,
                owner=payload.owner,
                tags=payload.tags,
            )
            self._projects[project.id] = project
            return project

    def _derive_task_status_locked(self, task_id: str) -> TaskStatus:
        command_ids = self._task_commands.get(task_id, [])
        if not command_ids:
            return TaskStatus.TODO

        statuses = {self._commands[command_id].status for command_id in command_ids}
        if CommandStatus.WAITING_APPROVAL in statuses:
            return TaskStatus.WAITING_APPROVAL
        if CommandStatus.RUNNING in statuses or CommandStatus.QUEUED in statuses:
            return TaskStatus.IN_PROGRESS
        if CommandStatus.FAILED in statuses:
            return TaskStatus.FAILED
        if CommandStatus.SUCCESS in statuses:
            return TaskStatus.DONE
        if CommandStatus.CANCELED in statuses:
            return TaskStatus.CANCELED
        return TaskStatus.TODO

    def _recompute_project_active_count_locked(self, project_id: str) -> None:
        project = self._projects.get(project_id)
        if project is None:
            return
        project.active_task_count = sum(
            1
            for task_id in self._project_tasks[project_id]
            if self._tasks[task_id].status
            in {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.WAITING_APPROVAL}
        )
        project.updated_at = now_utc()

    def _refresh_task_and_project_state_locked(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            return
        task.status = self._derive_task_status_locked(task_id)
        task.updated_at = now_utc()
        self._recompute_project_active_count_locked(task.project_id)

    def _advance_task_commands_locked(self, task_id: str) -> None:
        for command_id in self._task_commands.get(task_id, []):
            self._advance_command_locked(command_id)

    def _advance_all_commands_locked(self) -> None:
        for command_id in list(self._commands.keys()):
            self._advance_command_locked(command_id)

    def _advance_command_locked(self, command_id: str) -> None:
        command = self._commands.get(command_id)
        if command is None:
            return
        if command.status in {
            CommandStatus.SUCCESS,
            CommandStatus.FAILED,
            CommandStatus.CANCELED,
            CommandStatus.WAITING_APPROVAL,
        }:
            return

        if command.status == CommandStatus.QUEUED:
            command.status = CommandStatus.RUNNING
            command.started_at = now_utc()
            command.updated_at = now_utc()
            self._refresh_task_and_project_state_locked(command.task_id)
            return

        if command.status != CommandStatus.RUNNING:
            return

        started_at = command.started_at or now_utc()
        if now_utc() - started_at < timedelta(milliseconds=200):
            return

        task = self._tasks.get(command.task_id)
        if task is None:
            return

        lowered = command.text.lower()
        if "fail" in lowered or "error" in lowered:
            command.status = CommandStatus.FAILED
            command.error_message = "mock execution failed by command content"
            task.failed_count += 1
        else:
            command.status = CommandStatus.SUCCESS
            command.output_summary = "mock execution completed"
            task.success_count += 1

        command.finished_at = now_utc()
        command.updated_at = now_utc()
        self._refresh_task_and_project_state_locked(task.id)

    async def list_projects(self) -> list[Project]:
        async with self._lock:
            self._advance_all_commands_locked()
            return list(self._projects.values())

    async def create_task(self, project_id: str, payload: CreateTaskRequest) -> Task:
        async with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="project not found")

            task = Task(
                project_id=project_id,
                title=payload.title,
                description=payload.description,
                priority=payload.priority,
                assignee_agent=payload.assignee_agent,
            )
            self._tasks[task.id] = task
            self._project_tasks[project_id].append(task.id)

            project.task_count += 1
            self._refresh_task_and_project_state_locked(task.id)
            return task

    async def list_tasks(self, project_id: str) -> list[Task]:
        async with self._lock:
            if project_id not in self._projects:
                raise HTTPException(status_code=404, detail="project not found")
            for task_id in self._project_tasks[project_id]:
                self._advance_task_commands_locked(task_id)
            return [self._tasks[task_id] for task_id in self._project_tasks[project_id]]

    async def get_task(self, task_id: str) -> Task:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="task not found")
            self._advance_task_commands_locked(task_id)
            return task

    async def create_command(self, task_id: str, payload: CreateCommandRequest) -> Command:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="task not found")

            self._task_sequence[task_id] += 1
            command = Command(
                project_id=task.project_id,
                task_id=task_id,
                sequence=self._task_sequence[task_id],
                text=payload.text,
                source=payload.source,
                requested_by=payload.requested_by,
                requires_approval=payload.requires_approval,
                status=(
                    CommandStatus.WAITING_APPROVAL
                    if payload.requires_approval
                    else CommandStatus.QUEUED
                ),
            )

            self._commands[command.id] = command
            self._task_commands[task_id].append(command.id)

            task.command_count += 1
            task.last_command_id = command.id
            self._refresh_task_and_project_state_locked(task_id)

        return command

    async def list_commands(self, task_id: str) -> list[Command]:
        async with self._lock:
            if task_id not in self._tasks:
                raise HTTPException(status_code=404, detail="task not found")
            self._advance_task_commands_locked(task_id)
            return [self._commands[command_id] for command_id in self._task_commands[task_id]]

    async def get_command(self, command_id: str) -> Command:
        async with self._lock:
            command = self._commands.get(command_id)
            if command is None:
                raise HTTPException(status_code=404, detail="command not found")
            self._advance_command_locked(command_id)
            return command

    async def approve_command(self, command_id: str, approved_by: str) -> Command:
        async with self._lock:
            command = self._commands.get(command_id)
            if command is None:
                raise HTTPException(status_code=404, detail="command not found")
            if not command.requires_approval:
                raise HTTPException(status_code=409, detail="command does not require approval")
            if command.status != CommandStatus.WAITING_APPROVAL:
                raise HTTPException(status_code=409, detail="command is not waiting approval")

            command.approved_by = approved_by
            command.status = CommandStatus.QUEUED
            command.updated_at = now_utc()

            self._refresh_task_and_project_state_locked(command.task_id)

        return command

    async def get_project_detail(self, project_id: str) -> ProjectDetail:
        async with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="project not found")
            for task_id in self._project_tasks[project_id]:
                self._advance_task_commands_locked(task_id)

            task_details: list[TaskDetail] = []
            for task_id in self._project_tasks[project_id]:
                task = self._tasks[task_id]
                commands = [self._commands[cid] for cid in self._task_commands[task_id]]
                task_details.append(TaskDetail(**task.model_dump(), commands=commands))

            return ProjectDetail(**project.model_dump(), tasks=task_details)
