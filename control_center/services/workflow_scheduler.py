from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from control_center.models import (
    Artifact,
    ArtifactOwnerType,
    ArtifactType,
    DiscussionSession,
    DiscussionStatus,
    GateCheck,
    GateStatus,
    GateType,
    WorkItem,
    WorkItemStatus,
    WorkflowRun,
    WorkflowRunStatus,
)
from control_center.models.hierarchy import now_utc
from control_center.services.sqlite_state_store import SQLiteStateStore


class WorkflowScheduler:
    RUN_ENTITY_TYPE = "workflow_run"
    WORKITEM_ENTITY_TYPE = "workitem"
    DISCUSSION_ENTITY_TYPE = "discussion_session"
    GATE_ENTITY_TYPE = "gate_check"
    ARTIFACT_ENTITY_TYPE = "artifact"

    def __init__(self, state_store: SQLiteStateStore | None = None) -> None:
        self._runs: dict[str, WorkflowRun] = {}
        self._workitems: dict[str, WorkItem] = {}
        self._run_workitems: dict[str, list[str]] = defaultdict(list)
        self._workitem_run: dict[str, str] = {}
        self._discussions: dict[str, DiscussionSession] = {}
        self._workitem_discussions: dict[str, list[str]] = defaultdict(list)
        self._gate_checks: dict[str, GateCheck] = {}
        self._run_gate_checks: dict[str, list[str]] = defaultdict(list)
        self._workitem_gate_checks: dict[str, list[str]] = defaultdict(list)
        self._artifacts: dict[str, Artifact] = {}
        self._run_artifacts: dict[str, list[str]] = defaultdict(list)
        self._workitem_artifacts: dict[str, list[str]] = defaultdict(list)
        self._state_store = state_store
        self._load_state()

    def _load_state(self) -> None:
        if self._state_store is None:
            return

        runs = [
            WorkflowRun(**payload)
            for payload in self._state_store.list(self.RUN_ENTITY_TYPE)
        ]
        workitems = [
            WorkItem(**payload)
            for payload in self._state_store.list(self.WORKITEM_ENTITY_TYPE)
        ]
        discussions = [
            DiscussionSession(**payload)
            for payload in self._state_store.list(self.DISCUSSION_ENTITY_TYPE)
        ]
        gate_checks = [
            GateCheck(**payload)
            for payload in self._state_store.list(self.GATE_ENTITY_TYPE)
        ]
        artifacts = [
            Artifact(**payload)
            for payload in self._state_store.list(self.ARTIFACT_ENTITY_TYPE)
        ]

        self._runs = {run.id: run for run in runs}
        self._workitems = {item.id: item for item in workitems}
        self._discussions = {session.id: session for session in discussions}
        self._gate_checks = {gate.id: gate for gate in gate_checks}
        self._artifacts = {artifact.id: artifact for artifact in artifacts}
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        self._run_workitems = defaultdict(list)
        self._workitem_run = {}
        self._workitem_discussions = defaultdict(list)
        self._run_gate_checks = defaultdict(list)
        self._workitem_gate_checks = defaultdict(list)
        self._run_artifacts = defaultdict(list)
        self._workitem_artifacts = defaultdict(list)

        for item in sorted(self._workitems.values(), key=lambda value: value.created_at):
            self._run_workitems[item.workflow_run_id].append(item.id)
            self._workitem_run[item.id] = item.workflow_run_id

        for session in sorted(
            self._discussions.values(),
            key=lambda value: (value.workitem_id, value.round, value.created_at),
        ):
            self._workitem_discussions[session.workitem_id].append(session.id)

        for gate in sorted(
            self._gate_checks.values(),
            key=lambda value: (value.workitem_id, value.attempt, value.created_at),
        ):
            self._run_gate_checks[gate.workflow_run_id].append(gate.id)
            self._workitem_gate_checks[gate.workitem_id].append(gate.id)

        for artifact in sorted(self._artifacts.values(), key=lambda value: value.created_at):
            run_id: str | None = None
            if artifact.owner_type == ArtifactOwnerType.WORKITEM:
                workitem_id = artifact.owner_id
                self._workitem_artifacts[workitem_id].append(artifact.id)
                run_id = self._workitem_run.get(workitem_id)
            elif artifact.owner_type == ArtifactOwnerType.WORKFLOW_RUN:
                run_id = artifact.owner_id
            if run_id is not None:
                self._run_artifacts[run_id].append(artifact.id)

    def _persist_run(self, run: WorkflowRun) -> None:
        if self._state_store is None:
            return
        self._state_store.upsert(
            self.RUN_ENTITY_TYPE,
            run.id,
            run.model_dump(mode="json"),
        )

    def _persist_workitem(self, workitem: WorkItem) -> None:
        if self._state_store is None:
            return
        self._state_store.upsert(
            self.WORKITEM_ENTITY_TYPE,
            workitem.id,
            workitem.model_dump(mode="json"),
        )

    def _persist_discussion(self, session: DiscussionSession) -> None:
        if self._state_store is None:
            return
        self._state_store.upsert(
            self.DISCUSSION_ENTITY_TYPE,
            session.id,
            session.model_dump(mode="json"),
        )

    def _persist_gate(self, gate: GateCheck) -> None:
        if self._state_store is None:
            return
        self._state_store.upsert(
            self.GATE_ENTITY_TYPE,
            gate.id,
            gate.model_dump(mode="json"),
        )

    def _persist_artifact(self, artifact: Artifact) -> None:
        if self._state_store is None:
            return
        self._state_store.upsert(
            self.ARTIFACT_ENTITY_TYPE,
            artifact.id,
            artifact.model_dump(mode="json"),
        )

    def persist_run(self, run_id: str) -> WorkflowRun:
        run = self.get_run(run_id)
        run.updated_at = now_utc()
        self._persist_run(run)
        return run

    def create_run(
        self,
        project_id: str,
        *,
        task_id: str | None = None,
        template_id: str | None = None,
        requested_by: str | None = None,
        summary: str | None = None,
    ) -> WorkflowRun:
        run = WorkflowRun(
            project_id=project_id,
            task_id=task_id,
            template_id=template_id,
            requested_by=requested_by,
            summary=summary,
            status=WorkflowRunStatus.RUNNING,
        )
        self._runs[run.id] = run
        self._persist_run(run)
        return run

    def get_run(self, run_id: str) -> WorkflowRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"workflow run not found: {run_id}")
        return run

    def add_workitem(
        self,
        run_id: str,
        *,
        role: str,
        module_key: str | None = None,
        assignee_agent: str = "auto-agent",
        depends_on: list[str] | None = None,
        priority: int = 3,
        requires_approval: bool = False,
        discussion_budget: int = 2,
        discussion_timeout_seconds: int = 120,
        metadata: dict[str, object] | None = None,
    ) -> WorkItem:
        run = self.get_run(run_id)
        normalized_depends = depends_on or []
        self._validate_dependencies(run.id, normalized_depends)

        workitem = WorkItem(
            workflow_run_id=run.id,
            module_key=module_key,
            role=role,
            assignee_agent=assignee_agent,
            depends_on=normalized_depends,
            priority=priority,
            requires_approval=requires_approval,
            discussion_budget=discussion_budget,
            discussion_timeout_seconds=discussion_timeout_seconds,
            status=WorkItemStatus.PENDING,
            metadata=metadata or {},
        )
        self._workitems[workitem.id] = workitem
        self._run_workitems[run.id].append(workitem.id)
        self._workitem_run[workitem.id] = run.id
        run.updated_at = now_utc()
        self._persist_workitem(workitem)
        self._persist_run(run)
        return workitem

    def get_workitem(self, workitem_id: str) -> WorkItem:
        workitem = self._workitems.get(workitem_id)
        if workitem is None:
            raise KeyError(f"workitem not found: {workitem_id}")
        return workitem

    def list_workitems(self, run_id: str) -> list[WorkItem]:
        _ = self.get_run(run_id)
        return [self._workitems[item_id] for item_id in self._run_workitems[run_id]]

    def list_discussions(self, workitem_id: str) -> list[DiscussionSession]:
        _ = self.get_workitem(workitem_id)
        return [self._discussions[item_id] for item_id in self._workitem_discussions[workitem_id]]

    def create_gate_check(
        self,
        workitem_id: str,
        *,
        gate_type: GateType,
        passed: bool,
        summary: str,
        executed_by: str,
        evidence_artifact_ids: list[str] | None = None,
    ) -> GateCheck:
        item = self.get_workitem(workitem_id)
        run_id = item.workflow_run_id
        attempt = len(self._workitem_gate_checks[workitem_id]) + 1
        gate = GateCheck(
            workflow_run_id=run_id,
            workitem_id=workitem_id,
            gate_type=gate_type,
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            summary=summary,
            evidence_artifact_ids=evidence_artifact_ids or [],
            attempt=attempt,
            executed_by=executed_by,
        )
        self._gate_checks[gate.id] = gate
        self._run_gate_checks[run_id].append(gate.id)
        self._workitem_gate_checks[workitem_id].append(gate.id)
        self._persist_gate(gate)
        return gate

    def list_gate_checks(self, run_id: str) -> list[GateCheck]:
        _ = self.get_run(run_id)
        return [self._gate_checks[item_id] for item_id in self._run_gate_checks[run_id]]

    def create_artifact(
        self,
        workitem_id: str,
        *,
        artifact_type: ArtifactType,
        title: str,
        uri_or_path: str,
        created_by: str,
        checksum: str | None = None,
    ) -> Artifact:
        item = self.get_workitem(workitem_id)
        artifact = Artifact(
            owner_type=ArtifactOwnerType.WORKITEM,
            owner_id=workitem_id,
            artifact_type=artifact_type,
            title=title,
            uri_or_path=uri_or_path,
            created_by=created_by,
            checksum=checksum,
        )
        self._artifacts[artifact.id] = artifact
        self._run_artifacts[item.workflow_run_id].append(artifact.id)
        self._workitem_artifacts[workitem_id].append(artifact.id)
        self._persist_artifact(artifact)
        return artifact

    def list_artifacts(self, run_id: str) -> list[Artifact]:
        _ = self.get_run(run_id)
        return [self._artifacts[item_id] for item_id in self._run_artifacts[run_id]]

    def get_metrics(self) -> dict[str, object]:
        run_status_counts: dict[str, int] = {}
        for run in self._runs.values():
            key = run.status.value
            run_status_counts[key] = run_status_counts.get(key, 0) + 1

        workitem_status_counts: dict[str, int] = {}
        for item in self._workitems.values():
            key = item.status.value
            workitem_status_counts[key] = workitem_status_counts.get(key, 0) + 1

        gate_status_counts: dict[str, int] = {}
        for gate in self._gate_checks.values():
            key = gate.status.value
            gate_status_counts[key] = gate_status_counts.get(key, 0) + 1

        artifact_type_counts: dict[str, int] = {}
        for artifact in self._artifacts.values():
            key = artifact.artifact_type.value
            artifact_type_counts[key] = artifact_type_counts.get(key, 0) + 1

        return {
            "total_runs": len(self._runs),
            "run_status_counts": run_status_counts,
            "total_workitems": len(self._workitems),
            "workitem_status_counts": workitem_status_counts,
            "total_gate_checks": len(self._gate_checks),
            "gate_status_counts": gate_status_counts,
            "total_artifacts": len(self._artifacts),
            "artifact_type_counts": artifact_type_counts,
        }

    def tick(self, run_id: str) -> list[WorkItem]:
        run = self.get_run(run_id)
        ready: list[WorkItem] = []
        for item_id in self._run_workitems[run_id]:
            item = self._workitems[item_id]
            if item.status != WorkItemStatus.PENDING:
                continue
            if self._dependencies_satisfied(item):
                if item.requires_approval:
                    item.status = WorkItemStatus.WAITING_APPROVAL
                else:
                    item.status = WorkItemStatus.READY
                item.updated_at = now_utc()
                self._persist_workitem(item)
                if item.status == WorkItemStatus.READY:
                    ready.append(item)
        self._refresh_run_status(run)
        return sorted(ready, key=lambda item: (item.priority, item.created_at))

    def start_workitem(self, workitem_id: str) -> WorkItem:
        item = self.get_workitem(workitem_id)
        if item.status != WorkItemStatus.READY:
            raise ValueError(f"workitem {workitem_id} is not ready")
        item.status = WorkItemStatus.RUNNING
        item.started_at = now_utc()
        item.updated_at = now_utc()
        self._persist_workitem(item)
        run = self.get_run(self._workitem_run[workitem_id])
        self._refresh_run_status(run)
        return item

    def complete_workitem(self, workitem_id: str, *, success: bool) -> WorkItem:
        item = self.get_workitem(workitem_id)
        if item.status not in {WorkItemStatus.RUNNING, WorkItemStatus.READY}:
            raise ValueError(f"workitem {workitem_id} is not running")
        if item.started_at is None:
            item.started_at = now_utc()
        item.status = WorkItemStatus.SUCCEEDED if success else WorkItemStatus.FAILED
        item.finished_at = now_utc()
        item.updated_at = now_utc()
        self._persist_workitem(item)
        run = self.get_run(self._workitem_run[workitem_id])
        self._refresh_run_status(run)
        return item

    def approve_workitem(self, workitem_id: str, *, approved_by: str) -> WorkItem:
        item = self.get_workitem(workitem_id)
        if not item.requires_approval:
            raise ValueError(f"workitem {workitem_id} does not require approval")
        if item.status != WorkItemStatus.WAITING_APPROVAL:
            raise ValueError(f"workitem {workitem_id} is not waiting approval")
        item.status = WorkItemStatus.READY
        item.updated_at = now_utc()
        item.metadata["approved_by"] = approved_by
        self._persist_workitem(item)
        run = self.get_run(self._workitem_run[workitem_id])
        self._refresh_run_status(run)
        return item

    def mark_needs_discussion(
        self,
        workitem_id: str,
        *,
        question: str,
        options: list[str] | None = None,
        recommendation: str | None = None,
        impact: str | None = None,
        fingerprint: str | None = None,
    ) -> DiscussionSession:
        item = self.get_workitem(workitem_id)
        if item.status not in {WorkItemStatus.RUNNING, WorkItemStatus.READY}:
            raise ValueError(f"workitem {workitem_id} is not executable for discussion")

        next_round = item.discussion_used + 1
        if next_round > item.discussion_budget:
            item.status = WorkItemStatus.FAILED
            item.updated_at = now_utc()
            item.metadata["discussion_error"] = "discussion_budget_exhausted"
            self._persist_workitem(item)
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
            self._save_discussion(exhausted)
            run = self.get_run(self._workitem_run[workitem_id])
            self._refresh_run_status(run)
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
            self._persist_workitem(item)
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
            self._save_discussion(exhausted)
            run = self.get_run(self._workitem_run[workitem_id])
            self._refresh_run_status(run)
            return exhausted

        item.discussion_used = next_round
        item.status = WorkItemStatus.NEEDS_DISCUSSION
        item.updated_at = now_utc()
        if fingerprint:
            fingerprints.append(fingerprint)
        item.metadata["discussion_fingerprints"] = fingerprints
        self._persist_workitem(item)

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
        self._save_discussion(session)
        run = self.get_run(self._workitem_run[workitem_id])
        self._refresh_run_status(run)
        return session

    def resolve_discussion(
        self,
        workitem_id: str,
        *,
        decision: str,
        resolved_by_role: str,
        discussion_id: str | None = None,
    ) -> DiscussionSession:
        item = self.get_workitem(workitem_id)
        if item.status != WorkItemStatus.NEEDS_DISCUSSION:
            raise ValueError(f"workitem {workitem_id} is not waiting discussion")

        session = self._get_open_discussion(workitem_id, discussion_id)
        now = now_utc()
        timeout_at = session.created_at + timedelta(seconds=item.discussion_timeout_seconds)
        if now > timeout_at:
            session.status = DiscussionStatus.TIMEOUT
            session.updated_at = now
            item.status = WorkItemStatus.FAILED
            item.updated_at = now
            item.metadata["discussion_error"] = "discussion_timeout"
            self._persist_discussion(session)
            self._persist_workitem(item)
            run = self.get_run(self._workitem_run[workitem_id])
            self._refresh_run_status(run)
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
        self._persist_discussion(session)
        self._persist_workitem(item)
        run = self.get_run(self._workitem_run[workitem_id])
        self._refresh_run_status(run)
        return session

    def update_workitem_dependencies(
        self,
        workitem_id: str,
        dependency_ids: list[str],
    ) -> WorkItem:
        item = self.get_workitem(workitem_id)
        run_id = self._workitem_run[workitem_id]
        self._validate_dependencies(run_id, dependency_ids)
        normalized = [value.strip() for value in dependency_ids if value.strip()]
        if item.id in normalized:
            raise ValueError("workitem cannot depend on itself")
        if len(set(normalized)) != len(normalized):
            raise ValueError("dependency ids must not contain duplicates")
        item.depends_on = normalized
        item.updated_at = now_utc()
        self._persist_workitem(item)
        run = self.get_run(run_id)
        self._refresh_run_status(run)
        return item

    def mark_workitem_skipped(self, workitem_id: str, *, reason: str) -> WorkItem:
        item = self.get_workitem(workitem_id)
        if item.status in {WorkItemStatus.SUCCEEDED, WorkItemStatus.FAILED, WorkItemStatus.SKIPPED}:
            return item
        item.status = WorkItemStatus.SKIPPED
        if item.started_at is None:
            item.started_at = now_utc()
        item.finished_at = now_utc()
        item.updated_at = now_utc()
        item.metadata["skip_reason"] = reason
        self._persist_workitem(item)
        run = self.get_run(self._workitem_run[workitem_id])
        self._refresh_run_status(run)
        return item

    def count_workitems_by_status(self, run_id: str, status: WorkItemStatus) -> int:
        return sum(
            1 for item in self.list_workitems(run_id) if item.status == status
        )

    def list_workitem_ids_by_status(self, run_id: str, status: WorkItemStatus) -> list[str]:
        return [item.id for item in self.list_workitems(run_id) if item.status == status]

    def _save_discussion(self, session: DiscussionSession) -> None:
        self._discussions[session.id] = session
        self._workitem_discussions[session.workitem_id].append(session.id)
        self._persist_discussion(session)

    def _get_open_discussion(
        self,
        workitem_id: str,
        discussion_id: str | None,
    ) -> DiscussionSession:
        sessions = self.list_discussions(workitem_id)
        if not sessions:
            raise ValueError(f"workitem {workitem_id} has no discussion sessions")

        if discussion_id is not None:
            session = self._discussions.get(discussion_id)
            if session is None or session.workitem_id != workitem_id:
                raise ValueError(f"discussion session not found: {discussion_id}")
            if session.status != DiscussionStatus.OPEN:
                raise ValueError(f"discussion session is not open: {discussion_id}")
            return session

        for session in reversed(sessions):
            if session.status == DiscussionStatus.OPEN:
                return session
        raise ValueError(f"workitem {workitem_id} has no open discussion session")

    def _validate_dependencies(self, run_id: str, dependency_ids: list[str]) -> None:
        for dependency_id in dependency_ids:
            if dependency_id not in self._workitems:
                raise ValueError(f"dependency workitem not found: {dependency_id}")
            dependency_run_id = self._workitem_run.get(dependency_id)
            if dependency_run_id != run_id:
                raise ValueError(f"dependency workitem {dependency_id} is in another workflow run")

    def _dependencies_satisfied(self, item: WorkItem) -> bool:
        if not item.depends_on:
            return True
        for dependency_id in item.depends_on:
            dependency = self._workitems.get(dependency_id)
            if dependency is None:
                return False
            if dependency.status not in {WorkItemStatus.SUCCEEDED, WorkItemStatus.SKIPPED}:
                return False
        return True

    def _refresh_run_status(self, run: WorkflowRun) -> None:
        items = self.list_workitems(run.id)
        if not items:
            run.status = WorkflowRunStatus.PLANNING
            run.updated_at = now_utc()
            self._persist_run(run)
            return

        statuses = {item.status for item in items}
        if WorkItemStatus.FAILED in statuses:
            run.status = WorkflowRunStatus.FAILED
        elif WorkItemStatus.NEEDS_DISCUSSION in statuses:
            run.status = WorkflowRunStatus.BLOCKED
        elif WorkItemStatus.WAITING_APPROVAL in statuses:
            run.status = WorkflowRunStatus.WAITING_APPROVAL
        elif statuses.issubset({WorkItemStatus.SUCCEEDED, WorkItemStatus.SKIPPED}):
            run.status = WorkflowRunStatus.SUCCEEDED
        else:
            run.status = WorkflowRunStatus.RUNNING
        run.updated_at = now_utc()
        self._persist_run(run)
