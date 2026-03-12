from __future__ import annotations

from pydantic import BaseModel, Field


class AgentRuleEntry(BaseModel):
    role: str
    executor: str
    scope: str
    profile_path: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class AgentRulesRegistryResponse(BaseModel):
    version: str
    updated_at: str | None = None
    source_path: str
    scopes: dict[str, list[AgentRuleEntry]] = Field(default_factory=dict)
    total_roles: int = Field(ge=0)
