from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

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
from control_center.services.workflow_scheduler_dependencies import (
    dependencies_satisfied,
    normalize_dependency_update_ids,
    select_pending_ready_for_transition,
    validate_dependency_ids,
)
from control_center.services.workflow_scheduler_indexes import (
    build_artifact_indexes,
    build_discussion_indexes,
    build_gate_indexes,
    build_workitem_indexes,
)
from control_center.services.workflow_scheduler_status import (
    build_scheduler_metrics,
    derive_run_status,
)
from control_center.services.workflow_scheduler_discussion import (
    mark_needs_discussion as mark_needs_discussion_impl,
    resolve_discussion as resolve_discussion_impl,
)


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
        self._run_workitems, self._workitem_run = build_workitem_indexes(self._workitems)
        self._workitem_discussions = build_discussion_indexes(self._discussions)
        self._run_gate_checks, self._workitem_gate_checks = build_gate_indexes(
            self._gate_checks
        )
        self._run_artifacts, self._workitem_artifacts = build_artifact_indexes(
            self._artifacts,
            self._workitem_run,
        )

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
        run.metadata.setdefault("sdd_stage_artifacts", {})
        run.next_action_hint = "start_intent_stage"
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

    def create_run_artifact(
        self,
        run_id: str,
        *,
        artifact_type: ArtifactType,
        title: str,
        uri_or_path: str,
        created_by: str,
        checksum: str | None = None,
    ) -> Artifact:
        _ = self.get_run(run_id)
        artifact = Artifact(
            owner_type=ArtifactOwnerType.WORKFLOW_RUN,
            owner_id=run_id,
            artifact_type=artifact_type,
            title=title,
            uri_or_path=uri_or_path,
            created_by=created_by,
            checksum=checksum,
        )
        self._artifacts[artifact.id] = artifact
        self._run_artifacts[run_id].append(artifact.id)
        self._persist_artifact(artifact)
        return artifact

    def list_artifacts(self, run_id: str) -> list[Artifact]:
        _ = self.get_run(run_id)
        return [self._artifacts[item_id] for item_id in self._run_artifacts[run_id]]

    def get_metrics(self) -> dict[str, object]:
        return build_scheduler_metrics(
            runs=self._runs,
            workitems=self._workitems,
            gate_checks=self._gate_checks,
            artifacts=self._artifacts,
        )

    def tick(self, run_id: str) -> list[WorkItem]:
        run = self.get_run(run_id)
        if run.status == WorkflowRunStatus.CANCELED:
            return []
        ready: list[WorkItem] = []
        pending_ready = select_pending_ready_for_transition(
            run_workitem_ids=self._run_workitems[run_id],
            workitems=self._workitems,
        )
        for item in pending_ready:
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
        run = self.get_run(self._workitem_run[workitem_id])
        if run.status == WorkflowRunStatus.CANCELED:
            raise ValueError(f"workflow run {run.id} is canceled")
        if item.status != WorkItemStatus.READY:
            raise ValueError(f"workitem {workitem_id} is not ready")
        item.status = WorkItemStatus.RUNNING
        item.started_at = now_utc()
        item.updated_at = now_utc()
        self._persist_workitem(item)
        self._refresh_run_status(run)
        return item

    def complete_workitem(self, workitem_id: str, *, success: bool) -> WorkItem:
        item = self.get_workitem(workitem_id)
        run = self.get_run(self._workitem_run[workitem_id])
        if run.status == WorkflowRunStatus.CANCELED:
            raise ValueError(f"workflow run {run.id} is canceled")
        if item.status not in {WorkItemStatus.RUNNING, WorkItemStatus.READY}:
            raise ValueError(f"workitem {workitem_id} is not running")
        if item.started_at is None:
            item.started_at = now_utc()
        item.status = WorkItemStatus.SUCCEEDED if success else WorkItemStatus.FAILED
        item.finished_at = now_utc()
        item.updated_at = now_utc()
        self._persist_workitem(item)
        self._refresh_run_status(run)
        return item

    def approve_workitem(self, workitem_id: str, *, approved_by: str) -> WorkItem:
        item = self.get_workitem(workitem_id)
        run = self.get_run(self._workitem_run[workitem_id])
        if run.status == WorkflowRunStatus.CANCELED:
            raise ValueError(f"workflow run {run.id} is canceled")
        if not item.requires_approval:
            raise ValueError(f"workitem {workitem_id} does not require approval")
        if item.status != WorkItemStatus.WAITING_APPROVAL:
            raise ValueError(f"workitem {workitem_id} is not waiting approval")
        item.status = WorkItemStatus.READY
        item.updated_at = now_utc()
        item.metadata["approved_by"] = approved_by
        self._persist_workitem(item)
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
        return mark_needs_discussion_impl(
            self,
            workitem_id,
            question=question,
            options=options,
            recommendation=recommendation,
            impact=impact,
            fingerprint=fingerprint,
        )

    def resolve_discussion(
        self,
        workitem_id: str,
        *,
        decision: str,
        resolved_by_role: str,
        discussion_id: str | None = None,
    ) -> DiscussionSession:
        return resolve_discussion_impl(
            self,
            workitem_id,
            decision=decision,
            resolved_by_role=resolved_by_role,
            discussion_id=discussion_id,
        )

    def update_workitem_dependencies(
        self,
        workitem_id: str,
        dependency_ids: list[str],
    ) -> WorkItem:
        item = self.get_workitem(workitem_id)
        run_id = self._workitem_run[workitem_id]
        run = self.get_run(run_id)
        if run.status == WorkflowRunStatus.CANCELED:
            raise ValueError(f"workflow run {run.id} is canceled")
        self._validate_dependencies(run_id, dependency_ids)
        normalized = normalize_dependency_update_ids(
            workitem_id=item.id,
            dependency_ids=dependency_ids,
        )
        item.depends_on = normalized
        item.updated_at = now_utc()
        self._persist_workitem(item)
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

    def interrupt_run(
        self,
        run_id: str,
        *,
        requested_by: str | None = None,
        reason: str | None = None,
        skip_non_terminal_workitems: bool = True,
    ) -> tuple[WorkflowRunStatus, WorkflowRunStatus, bool, list[str]]:
        run = self.get_run(run_id)
        previous_status = run.status
        if run.status in {
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELED,
        }:
            return previous_status, run.status, False, []

        skipped_workitem_ids: list[str] = []
        if skip_non_terminal_workitems:
            for item in self.list_workitems(run_id):
                if item.status in {
                    WorkItemStatus.PENDING,
                    WorkItemStatus.READY,
                    WorkItemStatus.RUNNING,
                    WorkItemStatus.NEEDS_DISCUSSION,
                    WorkItemStatus.WAITING_APPROVAL,
                }:
                    item.status = WorkItemStatus.SKIPPED
                    if item.started_at is None:
                        item.started_at = now_utc()
                    item.finished_at = now_utc()
                    item.updated_at = now_utc()
                    item.metadata["skip_reason"] = "workflow_run_interrupted"
                    if requested_by:
                        item.metadata["interrupt_requested_by"] = requested_by
                    if reason:
                        item.metadata["interrupt_reason"] = reason
                    self._persist_workitem(item)
                    skipped_workitem_ids.append(item.id)

        run.status = WorkflowRunStatus.CANCELED
        run.updated_at = now_utc()
        run.metadata["interrupt"] = {
            "requested_by": requested_by,
            "reason": reason,
            "applied": True,
            "skip_non_terminal_workitems": bool(skip_non_terminal_workitems),
            "skipped_workitem_ids": list(skipped_workitem_ids),
        }
        self._persist_run(run)
        return previous_status, run.status, True, skipped_workitem_ids

    def restart_run(
        self,
        run_id: str,
        *,
        requested_by: str | None = None,
        reason: str | None = None,
        copy_decomposition: bool = True,
    ) -> tuple[WorkflowRun, bool]:
        source_run = self.get_run(run_id)
        if source_run.status not in {
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.CANCELED,
        }:
            raise ValueError(
                "restart is only allowed for terminal workflow runs: "
                "failed/succeeded/canceled"
            )

        restarted_run = self.create_run(
            project_id=source_run.project_id,
            task_id=source_run.task_id,
            template_id=source_run.template_id,
            requested_by=requested_by or source_run.requested_by,
            summary=source_run.summary,
        )
        restart_metadata: dict[str, object] = {
            "source_run_id": source_run.id,
            "requested_by": requested_by,
            "reason": reason,
            "copied_decomposition": False,
        }
        if copy_decomposition:
            chief_decomposition = source_run.metadata.get("chief_decomposition")
            if isinstance(chief_decomposition, dict):
                restarted_run.metadata["chief_decomposition"] = deepcopy(chief_decomposition)
                restart_metadata["copied_decomposition"] = True

        restarted_run.metadata["restart"] = restart_metadata
        self._persist_run(restarted_run)
        return restarted_run, bool(restart_metadata["copied_decomposition"])

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
        validate_dependency_ids(
            run_id,
            dependency_ids,
            self._workitems,
            self._workitem_run,
        )

    def _dependencies_satisfied(self, item: WorkItem) -> bool:
        return dependencies_satisfied(item, self._workitems)

    def _refresh_run_status(self, run: WorkflowRun) -> None:
        if run.status == WorkflowRunStatus.CANCELED:
            self._persist_run(run)
            return
        items = self.list_workitems(run.id)
        run.status = derive_run_status(items)
        run.updated_at = now_utc()
        self._persist_run(run)
