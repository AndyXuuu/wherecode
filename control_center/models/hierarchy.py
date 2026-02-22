from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"


class CommandStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    CANCELED = "canceled"


class CommandSource(str, Enum):
    USER = "user"
    AGENT = "agent"
    AUTOMATION = "automation"
    SYSTEM = "system"


class BaseEntity(BaseModel):
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Command(BaseEntity):
    id: str = Field(default_factory=lambda: new_id("cmd"))
    project_id: str
    task_id: str
    sequence: int = Field(ge=1)
    text: str = Field(min_length=1)
    source: CommandSource = CommandSource.USER
    status: CommandStatus = CommandStatus.QUEUED
    output_summary: str | None = None
    error_message: str | None = None
    requested_by: str | None = None
    requires_approval: bool = False
    approved_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> Command:
        if self.started_at and self.finished_at and self.started_at > self.finished_at:
            raise ValueError("started_at must be earlier than finished_at")
        return self


class Task(BaseEntity):
    id: str = Field(default_factory=lambda: new_id("task"))
    project_id: str
    title: str = Field(min_length=1)
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: int = Field(default=3, ge=1, le=5)
    assignee_agent: str | None = None
    command_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    last_command_id: str | None = None

    @model_validator(mode="after")
    def validate_counts(self) -> Task:
        if self.success_count + self.failed_count > self.command_count:
            raise ValueError("success_count + failed_count cannot exceed command_count")
        return self


class Project(BaseEntity):
    id: str = Field(default_factory=lambda: new_id("proj"))
    name: str = Field(min_length=1)
    description: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner: str | None = None
    task_count: int = Field(default=0, ge=0)
    active_task_count: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_task_counts(self) -> Project:
        if self.active_task_count > self.task_count:
            raise ValueError("active_task_count cannot exceed task_count")
        return self


class TaskDetail(Task):
    commands: list[Command] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_relation(self) -> TaskDetail:
        for cmd in self.commands:
            if cmd.task_id != self.id:
                raise ValueError("every command.task_id must match task.id")
            if cmd.project_id != self.project_id:
                raise ValueError("every command.project_id must match task.project_id")
        return self


class ProjectDetail(Project):
    tasks: list[TaskDetail] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_relation(self) -> ProjectDetail:
        for task in self.tasks:
            if task.project_id != self.id:
                raise ValueError("every task.project_id must match project.id")
        return self


class HierarchySnapshot(BaseModel):
    projects: list[ProjectDetail] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=now_utc)
