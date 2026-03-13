from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ExecutionStrategy(str, Enum):
    NATIVE = "native"
    OHMY = "ohmy"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_DISCUSSION = "needs_discussion"


class ExecutionError(BaseModel):
    code: str = Field(min_length=1)
    retryable: bool = False
    message: str = Field(min_length=1)


class ExecutionArtifact(BaseModel):
    name: str = Field(min_length=1)
    uri_or_path: str = Field(min_length=1)


class ExecutionRequest(BaseModel):
    run_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    context_ref: str = Field(min_length=1)
    strategy: ExecutionStrategy = ExecutionStrategy.NATIVE
    model: str | None = None
    timeout_seconds: int = Field(default=180, ge=1, le=7200)


class ExecutionResult(BaseModel):
    status: ExecutionStatus
    summary: str
    trace_id: str
    artifacts: list[ExecutionArtifact] = Field(default_factory=list)
    error: ExecutionError | None = None
    raw_ref: str = ""
