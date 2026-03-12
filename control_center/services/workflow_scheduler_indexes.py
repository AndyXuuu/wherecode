from __future__ import annotations

from collections import defaultdict

from control_center.models import Artifact, ArtifactOwnerType, DiscussionSession, GateCheck, WorkItem


def build_workitem_indexes(
    workitems: dict[str, WorkItem],
) -> tuple[defaultdict[str, list[str]], dict[str, str]]:
    run_workitems: defaultdict[str, list[str]] = defaultdict(list)
    workitem_run: dict[str, str] = {}
    for item in sorted(workitems.values(), key=lambda value: value.created_at):
        run_workitems[item.workflow_run_id].append(item.id)
        workitem_run[item.id] = item.workflow_run_id
    return run_workitems, workitem_run


def build_discussion_indexes(
    discussions: dict[str, DiscussionSession],
) -> defaultdict[str, list[str]]:
    workitem_discussions: defaultdict[str, list[str]] = defaultdict(list)
    for session in sorted(
        discussions.values(),
        key=lambda value: (value.workitem_id, value.round, value.created_at),
    ):
        workitem_discussions[session.workitem_id].append(session.id)
    return workitem_discussions


def build_gate_indexes(
    gate_checks: dict[str, GateCheck],
) -> tuple[defaultdict[str, list[str]], defaultdict[str, list[str]]]:
    run_gate_checks: defaultdict[str, list[str]] = defaultdict(list)
    workitem_gate_checks: defaultdict[str, list[str]] = defaultdict(list)
    for gate in sorted(
        gate_checks.values(),
        key=lambda value: (value.workitem_id, value.attempt, value.created_at),
    ):
        run_gate_checks[gate.workflow_run_id].append(gate.id)
        workitem_gate_checks[gate.workitem_id].append(gate.id)
    return run_gate_checks, workitem_gate_checks


def build_artifact_indexes(
    artifacts: dict[str, Artifact],
    workitem_run: dict[str, str],
) -> tuple[defaultdict[str, list[str]], defaultdict[str, list[str]]]:
    run_artifacts: defaultdict[str, list[str]] = defaultdict(list)
    workitem_artifacts: defaultdict[str, list[str]] = defaultdict(list)
    for artifact in sorted(artifacts.values(), key=lambda value: value.created_at):
        run_id: str | None = None
        if artifact.owner_type == ArtifactOwnerType.WORKITEM:
            workitem_id = artifact.owner_id
            workitem_artifacts[workitem_id].append(artifact.id)
            run_id = workitem_run.get(workitem_id)
        elif artifact.owner_type == ArtifactOwnerType.WORKFLOW_RUN:
            run_id = artifact.owner_id
        if run_id is not None:
            run_artifacts[run_id].append(artifact.id)
    return run_artifacts, workitem_artifacts
