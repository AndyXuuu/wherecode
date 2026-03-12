from __future__ import annotations

from datetime import timedelta

from control_center.models import DiscussionSession, DiscussionStatus, WorkItemStatus
from control_center.models.hierarchy import now_utc


def mark_needs_discussion(
    scheduler,
    workitem_id: str,
    *,
    question: str,
    options: list[str] | None = None,
    recommendation: str | None = None,
    impact: str | None = None,
    fingerprint: str | None = None,
) -> DiscussionSession:
    item = scheduler.get_workitem(workitem_id)
    if item.status not in {WorkItemStatus.RUNNING, WorkItemStatus.READY}:
        raise ValueError(f"workitem {workitem_id} is not executable for discussion")

    next_round = item.discussion_used + 1
    if next_round > item.discussion_budget:
        item.status = WorkItemStatus.FAILED
        item.updated_at = now_utc()
        item.metadata["discussion_error"] = "discussion_budget_exhausted"
        scheduler._persist_workitem(item)
        exhausted = DiscussionSession(
            workflow_run_id=item.workflow_run_id,
            workitem_id=item.id,
            status=DiscussionStatus.EXHAUSTED,
            question=question,
            options=options or [],
            recommendation=recommendation,
            impact=impact,
            round=next_round,
            budget=item.discussion_budget,
            fingerprint=fingerprint,
            opened_by_role=item.role,
        )
        scheduler._save_discussion(exhausted)
        run = scheduler.get_run(scheduler._workitem_run[workitem_id])
        scheduler._refresh_run_status(run)
        return exhausted

    fingerprints: list[str] = [
        value
        for value in item.metadata.get("discussion_fingerprints", [])
        if isinstance(value, str)
    ]
    if fingerprint and fingerprint in fingerprints:
        item.status = WorkItemStatus.FAILED
        item.updated_at = now_utc()
        item.metadata["discussion_error"] = "discussion_loop_detected"
        scheduler._persist_workitem(item)
        exhausted = DiscussionSession(
            workflow_run_id=item.workflow_run_id,
            workitem_id=item.id,
            status=DiscussionStatus.EXHAUSTED,
            question=question,
            options=options or [],
            recommendation=recommendation,
            impact=impact,
            round=next_round,
            budget=item.discussion_budget,
            fingerprint=fingerprint,
            opened_by_role=item.role,
        )
        scheduler._save_discussion(exhausted)
        run = scheduler.get_run(scheduler._workitem_run[workitem_id])
        scheduler._refresh_run_status(run)
        return exhausted

    item.discussion_used = next_round
    item.status = WorkItemStatus.NEEDS_DISCUSSION
    item.updated_at = now_utc()
    if fingerprint:
        fingerprints.append(fingerprint)
    item.metadata["discussion_fingerprints"] = fingerprints
    scheduler._persist_workitem(item)

    session = DiscussionSession(
        workflow_run_id=item.workflow_run_id,
        workitem_id=item.id,
        status=DiscussionStatus.OPEN,
        question=question,
        options=options or [],
        recommendation=recommendation,
        impact=impact,
        round=next_round,
        budget=item.discussion_budget,
        fingerprint=fingerprint,
        opened_by_role=item.role,
    )
    scheduler._save_discussion(session)
    run = scheduler.get_run(scheduler._workitem_run[workitem_id])
    scheduler._refresh_run_status(run)
    return session


def resolve_discussion(
    scheduler,
    workitem_id: str,
    *,
    decision: str,
    resolved_by_role: str,
    discussion_id: str | None = None,
) -> DiscussionSession:
    item = scheduler.get_workitem(workitem_id)
    if item.status != WorkItemStatus.NEEDS_DISCUSSION:
        raise ValueError(f"workitem {workitem_id} is not waiting discussion")

    session = scheduler._get_open_discussion(workitem_id, discussion_id)
    now = now_utc()
    timeout_at = session.created_at + timedelta(seconds=item.discussion_timeout_seconds)
    if now > timeout_at:
        session.status = DiscussionStatus.TIMEOUT
        session.updated_at = now
        item.status = WorkItemStatus.FAILED
        item.updated_at = now
        item.metadata["discussion_error"] = "discussion_timeout"
        scheduler._persist_discussion(session)
        scheduler._persist_workitem(item)
        run = scheduler.get_run(scheduler._workitem_run[workitem_id])
        scheduler._refresh_run_status(run)
        return session

    session.status = DiscussionStatus.RESOLVED
    session.decision = decision
    session.resolved_by_role = resolved_by_role
    session.updated_at = now

    item.status = WorkItemStatus.READY
    item.updated_at = now
    item.metadata["discussion_decision"] = decision
    item.metadata["discussion_resolved_by"] = resolved_by_role
    item.metadata["discussion_resolved"] = True
    scheduler._persist_discussion(session)
    scheduler._persist_workitem(item)
    run = scheduler.get_run(scheduler._workitem_run[workitem_id])
    scheduler._refresh_run_status(run)
    return session
