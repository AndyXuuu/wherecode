from __future__ import annotations

from pydantic import BaseModel, Field

from control_center.models.hierarchy import CommandSource, CommandStatus


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    assignee_agent: str | None = None


class CreateCommandRequest(BaseModel):
    text: str = Field(min_length=1)
    source: CommandSource = CommandSource.USER
    requested_by: str | None = None
    requires_approval: bool = False


class ApproveCommandRequest(BaseModel):
    approved_by: str = Field(min_length=1)


class CommandAcceptedResponse(BaseModel):
    command_id: str
    task_id: str
    project_id: str
    status: CommandStatus
    poll_url: str


class ActionLayerHealthResponse(BaseModel):
    status: str
    layer: str
    transport: str


class ActionExecuteRequest(BaseModel):
    text: str = Field(min_length=1)
    requested_by: str | None = None
    task_id: str | None = None
    project_id: str | None = None


class ActionExecuteResponse(BaseModel):
    status: str
    summary: str
    agent: str
    trace_id: str
