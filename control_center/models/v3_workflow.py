from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from control_center.models.hierarchy import new_id, now_utc


class WorkflowRunStatus(str, Enum):
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class WorkItemStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    NEEDS_DISCUSSION = "needs_discussion"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"


class GateStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"


class DiscussionStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    EXHAUSTED = "exhausted"
    TIMEOUT = "timeout"


class GateType(str, Enum):
    DOC = "doc"
    TEST = "test"
    SECURITY = "security"
    ACCEPTANCE = "acceptance"
    RELEASE = "release"


class ArtifactOwnerType(str, Enum):
    WORKITEM = "workitem"
    TASK = "task"
    COMMAND = "command"
    WORKFLOW_RUN = "workflow_run"


class ArtifactType(str, Enum):
    PLAN = "plan"
    DIFF_SUMMARY = "diff_summary"
    TEST_REPORT = "test_report"
    DOC_UPDATE = "doc_update"
    SECURITY_REPORT = "security_report"
    ACCEPTANCE_REPORT = "acceptance_report"
    RELEASE_NOTE = "release_note"
    ROLLBACK_PLAN = "rollback_plan"


class V3BaseEntity(BaseModel):
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowTemplate(V3BaseEntity):
    id: str = Field(default_factory=lambda: new_id("wft"))
    name: str = Field(min_length=1)
    description: str | None = None
    module_stages: list[str] = Field(
        default_factory=lambda: [
            "module-dev",
            "doc-manager",
            "qa-test",
            "security-review",
        ]
    )
    global_stages: list[str] = Field(
        default_factory=lambda: [
            "integration-test",
            "acceptance",
            "release-manager",
        ]
    )
    active: bool = True


class WorkflowRun(V3BaseEntity):
    id: str = Field(default_factory=lambda: new_id("wfr"))
    project_id: str = Field(min_length=1)
    task_id: str | None = None
    template_id: str | None = None
    status: WorkflowRunStatus = WorkflowRunStatus.PLANNING
    requested_by: str | None = None
    summary: str | None = None


class WorkItem(V3BaseEntity):
    id: str = Field(default_factory=lambda: new_id("wi"))
    workflow_run_id: str = Field(min_length=1)
    module_key: str | None = None
    role: str = Field(min_length=1)
    assignee_agent: str = Field(default="auto-agent", min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    status: WorkItemStatus = WorkItemStatus.PENDING
    priority: int = Field(default=3, ge=1, le=5)
    discussion_budget: int = Field(default=2, ge=0)
    discussion_used: int = Field(default=0, ge=0)
    discussion_timeout_seconds: int = Field(default=120, ge=1)
    loop_guard_fingerprint: str | None = None
    requires_approval: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def validate_constraints(self) -> WorkItem:
        if self.discussion_used > self.discussion_budget:
            raise ValueError("discussion_used cannot exceed discussion_budget")

        if self.started_at and self.finished_at and self.started_at > self.finished_at:
            raise ValueError("started_at must be earlier than finished_at")

        normalized_depends = [item.strip() for item in self.depends_on if item.strip()]
        if len(set(normalized_depends)) != len(normalized_depends):
            raise ValueError("depends_on must not contain duplicate ids")
        if self.id in normalized_depends:
            raise ValueError("depends_on must not reference itself")

        self.depends_on = normalized_depends
        return self


class GateCheck(BaseModel):
    id: str = Field(default_factory=lambda: new_id("gate"))
    workflow_run_id: str = Field(min_length=1)
    workitem_id: str = Field(min_length=1)
    gate_type: GateType
    status: GateStatus = GateStatus.NOT_STARTED
    summary: str | None = None
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    attempt: int = Field(default=1, ge=1)
    executed_by: str | None = None
    created_at: datetime = Field(default_factory=now_utc)


class DiscussionSession(BaseModel):
    id: str = Field(default_factory=lambda: new_id("disc"))
    workflow_run_id: str = Field(min_length=1)
    workitem_id: str = Field(min_length=1)
    status: DiscussionStatus = DiscussionStatus.OPEN
    question: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    impact: str | None = None
    decision: str | None = None
    round: int = Field(default=1, ge=1)
    budget: int = Field(default=2, ge=0)
    fingerprint: str | None = None
    opened_by_role: str = Field(min_length=1)
    resolved_by_role: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    @model_validator(mode="after")
    def validate_constraints(self) -> DiscussionSession:
        if len(self.options) > 3:
            raise ValueError("options length must be <= 3")
        if self.round > self.budget and self.status != DiscussionStatus.EXHAUSTED:
            raise ValueError("round exceeded budget, status must be exhausted")
        if self.status == DiscussionStatus.RESOLVED and not self.decision:
            raise ValueError("decision is required when status is resolved")
        return self


class Artifact(BaseModel):
    id: str = Field(default_factory=lambda: new_id("art"))
    owner_type: ArtifactOwnerType
    owner_id: str = Field(min_length=1)
    artifact_type: ArtifactType
    title: str = Field(min_length=1)
    uri_or_path: str = Field(min_length=1)
    checksum: str | None = None
    created_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=now_utc)
