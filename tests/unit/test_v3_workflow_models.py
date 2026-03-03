from datetime import timedelta

from pydantic import ValidationError

from control_center.models import (
    Artifact,
    ArtifactOwnerType,
    ArtifactType,
    DiscussionSession,
    DiscussionStatus,
    GateCheck,
    GateStatus,
    GateType,
    WorkflowRun,
    WorkItem,
)
from control_center.models.hierarchy import now_utc


def test_workflow_run_has_prefixed_id() -> None:
    workflow_run = WorkflowRun(project_id="proj_alpha")
    assert workflow_run.id.startswith("wfr_")


def test_workitem_rejects_discussion_used_above_budget() -> None:
    with_validation_error = False
    try:
        WorkItem(
            workflow_run_id="wfr_alpha",
            role="module-dev",
            discussion_budget=1,
            discussion_used=2,
        )
    except ValidationError:
        with_validation_error = True

    assert with_validation_error


def test_workitem_rejects_invalid_timestamp_order() -> None:
    with_validation_error = False
    started = now_utc()
    try:
        WorkItem(
            workflow_run_id="wfr_alpha",
            role="qa-test",
            started_at=started,
            finished_at=started - timedelta(seconds=1),
        )
    except ValidationError:
        with_validation_error = True

    assert with_validation_error


def test_workitem_rejects_duplicate_dependencies() -> None:
    with_validation_error = False
    try:
        WorkItem(
            workflow_run_id="wfr_alpha",
            role="doc-manager",
            depends_on=["wi_1", "wi_1"],
        )
    except ValidationError:
        with_validation_error = True

    assert with_validation_error


def test_discussion_round_above_budget_requires_exhausted_status() -> None:
    with_validation_error = False
    try:
        DiscussionSession(
            workflow_run_id="wfr_alpha",
            workitem_id="wi_alpha",
            question="Need decision on test strategy",
            round=3,
            budget=2,
            status=DiscussionStatus.OPEN,
            opened_by_role="qa-test",
        )
    except ValidationError:
        with_validation_error = True

    assert with_validation_error


def test_discussion_resolved_requires_decision() -> None:
    with_validation_error = False
    try:
        DiscussionSession(
            workflow_run_id="wfr_alpha",
            workitem_id="wi_alpha",
            question="Pick rollout strategy",
            status=DiscussionStatus.RESOLVED,
            opened_by_role="chief-architect",
        )
    except ValidationError:
        with_validation_error = True

    assert with_validation_error


def test_gatecheck_and_artifact_valid_defaults() -> None:
    gate = GateCheck(
        workflow_run_id="wfr_alpha",
        workitem_id="wi_alpha",
        gate_type=GateType.DOC,
    )
    assert gate.id.startswith("gate_")
    assert gate.status == GateStatus.NOT_STARTED

    artifact = Artifact(
        owner_type=ArtifactOwnerType.WORKITEM,
        owner_id="wi_alpha",
        artifact_type=ArtifactType.DOC_UPDATE,
        title="Doc update summary",
        uri_or_path="docs/auth.md",
        created_by="doc-manager",
    )
    assert artifact.id.startswith("art_")
