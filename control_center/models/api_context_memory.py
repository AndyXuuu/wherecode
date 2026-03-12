from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MemoryNamespaceScope = Literal["shared", "project", "run"]


class ContextMemoryUpsertRequest(BaseModel):
    scope: MemoryNamespaceScope
    key: str = Field(min_length=1)
    value: object | None = None
    updated_by: str = Field(min_length=1)
    project_id: str | None = None
    run_id: str | None = None


class ContextMemoryItemResponse(BaseModel):
    scope: MemoryNamespaceScope
    namespace_id: str
    key: str
    value: object | None = None
    project_id: str | None = None
    run_id: str | None = None
    created_at: datetime
    updated_at: datetime
    updated_by: str
    version: int = Field(ge=1)


class ContextMemoryDeleteResponse(BaseModel):
    deleted: bool
    scope: MemoryNamespaceScope
    namespace_id: str
    key: str
    deleted_at: datetime


class ContextMemoryResolveResponse(BaseModel):
    scope_chain: list[str] = Field(default_factory=list)
    values: dict[str, object | None] = Field(default_factory=dict)
    source_namespaces: dict[str, str] = Field(default_factory=dict)
    resolved_at: datetime
