from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from action_layer.services import AgentRegistry, UnknownAgentRoleError

from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ArtifactType,
    DiscussionStatus,
    DiscussionPrompt,
    ExecuteWorkflowRunResponse,
    WorkItem,
    WorkItemStatus,
    WorkflowRunStatus,
)
from control_center.services.gatekeeper import Gatekeeper
from control_center.services.workflow_scheduler import WorkflowScheduler

ActionExecutor = Callable[[ActionExecuteRequest], Awaitable[ActionExecuteResponse]]


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    workitems: list[WorkItem]


class WorkflowEngine:
    MODULE_STAGES = ("module-dev", "doc-manager", "qa-test", "security-review")
    GLOBAL_STAGES = ("integration-test", "acceptance", "release-manager")

    def __init__(
        self,
        scheduler: WorkflowScheduler,
        action_executor: ActionExecutor,
        agent_registry: AgentRegistry | None = None,
        gatekeeper: Gatekeeper | None = None,
        max_module_reflows: int = 1,
        release_requires_approval: bool = False,
    ) -> None:
        self._scheduler = scheduler
        self._action_executor = action_executor
        self._agent_registry = agent_registry or AgentRegistry()
        self._gatekeeper = gatekeeper or Gatekeeper()
        self._max_module_reflows = max_module_reflows
        self._release_requires_approval = release_requires_approval

    def bootstrap_standard_pipeline(self, run_id: str, modules: list[str]) -> BootstrapResult:
        if self._scheduler.list_workitems(run_id):
            raise ValueError("workflow already has workitems")

        normalized_modules = self._normalize_modules(modules)
        created: list[WorkItem] = []
        module_terminal_ids: list[str] = []

        for module in normalized_modules:
            depends_on: list[str] = []
            for role in self.MODULE_STAGES:
                workitem = self._scheduler.add_workitem(
                    run_id=run_id,
                    role=role,
                    module_key=module,
                    depends_on=depends_on,
                )
                created.append(workitem)
                depends_on = [workitem.id]
            module_terminal_ids.extend(depends_on)

        global_depends_on = list(module_terminal_ids)
        for role in self.GLOBAL_STAGES:
            workitem = self._scheduler.add_workitem(
                run_id=run_id,
                role=role,
                module_key="global",
                depends_on=global_depends_on,
                requires_approval=(role == "release-manager" and self._release_requires_approval),
            )
            created.append(workitem)
            global_depends_on = [workitem.id]

        run = self._scheduler.get_run(run_id)
        run.metadata["module_terminal_workitems"] = {
            module: terminal_id
            for module, terminal_id in zip(normalized_modules, module_terminal_ids, strict=True)
        }
        run.metadata["reflow_attempts"] = {}
        self._scheduler.persist_run(run.id)
        return BootstrapResult(workitems=created)

    async def execute_until_blocked(
        self,
        run_id: str,
        *,
        max_loops: int = 20,
    ) -> ExecuteWorkflowRunResponse:
        if max_loops < 1:
            raise ValueError("max_loops must be >= 1")

        executed: list[str] = []
        failed: list[str] = []
        waiting_discussion: list[str] = []

        for _ in range(max_loops):
            ready = [
                item
                for item in self._scheduler.list_workitems(run_id)
                if item.status == WorkItemStatus.READY
            ]
            if not ready:
                ready = self._scheduler.tick(run_id)
            if not ready:
                break
            ready = sorted(ready, key=lambda item: (item.priority, item.created_at))

            for workitem in ready:
                self._scheduler.start_workitem(workitem.id)
                execution_status = await self._execute_one_workitem(workitem)
                executed.append(workitem.id)

                if execution_status == "success":
                    gated = self._apply_gate_and_reflow_if_needed(workitem)
                    if gated == "success":
                        self._scheduler.complete_workitem(workitem.id, success=True)
                        self._emit_artifacts_for_workitem(workitem)
                    elif gated == "reflowed":
                        self._scheduler.mark_workitem_skipped(
                            workitem.id,
                            reason="gate_failed_reflow",
                        )
                    else:
                        self._scheduler.complete_workitem(workitem.id, success=False)
                        failed.append(workitem.id)
                    continue

                if execution_status == "needs_discussion":
                    waiting_discussion.append(workitem.id)
                    continue

                self._scheduler.complete_workitem(workitem.id, success=False)
                failed.append(workitem.id)

        run = self._scheduler.get_run(run_id)
        all_workitems = self._scheduler.list_workitems(run_id)
        remaining_ready = [
            item.id for item in all_workitems if item.status == WorkItemStatus.READY
        ]
        remaining_pending = [
            item.id for item in all_workitems if item.status == WorkItemStatus.PENDING
        ]
        waiting_discussion_ids = self._scheduler.list_workitem_ids_by_status(
            run_id,
            WorkItemStatus.NEEDS_DISCUSSION,
        )
        waiting_approval_ids = self._scheduler.list_workitem_ids_by_status(
            run_id,
            WorkItemStatus.WAITING_APPROVAL,
        )
        return ExecuteWorkflowRunResponse(
            run_id=run.id,
            run_status=run.status,
            executed_count=len(executed),
            failed_count=len(failed),
            remaining_ready_count=len(remaining_ready),
            remaining_pending_count=len(remaining_pending),
            waiting_discussion_count=len(waiting_discussion_ids),
            waiting_approval_count=len(waiting_approval_ids),
            executed_workitem_ids=executed,
            failed_workitem_ids=failed,
            waiting_discussion_workitem_ids=waiting_discussion_ids,
            waiting_approval_workitem_ids=waiting_approval_ids,
        )

    async def _execute_one_workitem(self, workitem: WorkItem) -> str:
        role = workitem.role
        try:
            mapped_agent = self._agent_registry.resolve(role)
        except UnknownAgentRoleError as exc:
            workitem.metadata["execution_error"] = str(exc)
            return "failed"

        run = self._scheduler.get_run(workitem.workflow_run_id)
        request = ActionExecuteRequest(
            text=self._build_execution_text(workitem),
            agent=mapped_agent,
            project_id=run.project_id,
            task_id=run.task_id,
            requested_by=run.requested_by,
            role=workitem.role,
            module_key=workitem.module_key,
        )
        try:
            result = await self._action_executor(request)
        except Exception as exc:  # noqa: BLE001
            workitem.metadata["execution_error"] = str(exc)
            workitem.metadata["executor_agent"] = mapped_agent
            return "failed"

        workitem.metadata["executor_agent"] = result.agent
        workitem.metadata["trace_id"] = result.trace_id
        workitem.metadata["execution_summary"] = result.summary
        if result.metadata:
            workitem.metadata["execution_metadata"] = result.metadata
        if result.status == "needs_discussion":
            prompt = result.discussion or DiscussionPrompt(
                question="Need architecture decision",
                options=[],
            )
            discussion = self._scheduler.mark_needs_discussion(
                workitem.id,
                question=prompt.question,
                options=prompt.options,
                recommendation=prompt.recommendation,
                impact=prompt.impact,
                fingerprint=prompt.fingerprint,
            )
            if discussion.status == DiscussionStatus.OPEN:
                return "needs_discussion"
            return "failed"
        if result.status == "success":
            return "success"
        return "failed"

    def _apply_gate_and_reflow_if_needed(self, workitem: WorkItem) -> str:
        gate_decision = self._gatekeeper.evaluate(workitem)
        if gate_decision is None:
            return "success"

        gate = self._scheduler.create_gate_check(
            workitem.id,
            gate_type=gate_decision.gate_type,
            passed=gate_decision.passed,
            summary=gate_decision.summary,
            executed_by=gate_decision.executed_by,
        )
        workitem.metadata["gate_check_id"] = gate.id
        workitem.metadata["gate_type"] = gate_decision.gate_type.value
        workitem.metadata["gate_summary"] = gate_decision.summary

        if gate_decision.passed:
            return "success"

        reflow_applied = self._apply_module_reflow(workitem)
        if reflow_applied:
            workitem.metadata["reflow_applied"] = True
            return "reflowed"
        return "failed"

    def _apply_module_reflow(self, failed_workitem: WorkItem) -> bool:
        module = (failed_workitem.module_key or "").strip()
        if not module or module == "global":
            return False

        run = self._scheduler.get_run(failed_workitem.workflow_run_id)
        attempts = run.metadata.get("reflow_attempts")
        if not isinstance(attempts, dict):
            attempts = {}
        current_attempt = int(attempts.get(module, 0)) + 1
        attempts[module] = current_attempt
        run.metadata["reflow_attempts"] = attempts
        self._scheduler.persist_run(run.id)
        if current_attempt > self._max_module_reflows:
            failed_workitem.metadata["reflow_error"] = "reflow_budget_exhausted"
            return False

        obsolete = self._find_module_descendants(failed_workitem)
        for item in obsolete:
            self._scheduler.mark_workitem_skipped(item.id, reason="obsolete_after_reflow")

        new_depends = list(failed_workitem.depends_on)
        chain: list[WorkItem] = []
        for role in self.MODULE_STAGES:
            created = self._scheduler.add_workitem(
                run_id=run.id,
                role=role,
                module_key=module,
                depends_on=new_depends,
                metadata={"reflow_attempt": current_attempt},
            )
            chain.append(created)
            new_depends = [created.id]

        new_terminal = chain[-1]
        module_terminals = run.metadata.get("module_terminal_workitems")
        if not isinstance(module_terminals, dict):
            module_terminals = {}
        old_terminal_id = module_terminals.get(module)
        module_terminals[module] = new_terminal.id
        run.metadata["module_terminal_workitems"] = module_terminals
        self._scheduler.persist_run(run.id)

        if isinstance(old_terminal_id, str) and old_terminal_id:
            self._rewire_integration_dependencies(
                run.id,
                old_terminal_id=old_terminal_id,
                new_terminal_id=new_terminal.id,
            )
        return True

    def _find_module_descendants(self, failed_workitem: WorkItem) -> list[WorkItem]:
        run_items = self._scheduler.list_workitems(failed_workitem.workflow_run_id)
        target_module = failed_workitem.module_key
        pending_like = {
            WorkItemStatus.PENDING,
            WorkItemStatus.READY,
            WorkItemStatus.NEEDS_DISCUSSION,
            WorkItemStatus.RUNNING,
        }
        descendants: list[WorkItem] = []
        frontier = [failed_workitem.id]
        visited: set[str] = set()

        while frontier:
            current = frontier.pop()
            for item in run_items:
                if item.id in visited:
                    continue
                if current not in item.depends_on:
                    continue
                if item.module_key != target_module:
                    continue
                if item.status not in pending_like:
                    continue
                visited.add(item.id)
                descendants.append(item)
                frontier.append(item.id)
        return descendants

    def _rewire_integration_dependencies(
        self,
        run_id: str,
        *,
        old_terminal_id: str,
        new_terminal_id: str,
    ) -> None:
        for item in self._scheduler.list_workitems(run_id):
            if item.role != "integration-test":
                continue
            updated = [
                new_terminal_id if dep == old_terminal_id else dep for dep in item.depends_on
            ]
            if updated != item.depends_on:
                self._scheduler.update_workitem_dependencies(item.id, updated)

    def _emit_artifacts_for_workitem(self, workitem: WorkItem) -> None:
        role = workitem.role
        if role == "acceptance":
            self._scheduler.create_artifact(
                workitem.id,
                artifact_type=ArtifactType.ACCEPTANCE_REPORT,
                title=f"Acceptance report for {workitem.module_key or 'global'}",
                uri_or_path=f"artifacts/{workitem.id}/acceptance-report.md",
                created_by=role,
            )
            return
        if role == "release-manager":
            self._scheduler.create_artifact(
                workitem.id,
                artifact_type=ArtifactType.RELEASE_NOTE,
                title="Release note",
                uri_or_path=f"artifacts/{workitem.id}/release-note.md",
                created_by=role,
            )
            self._scheduler.create_artifact(
                workitem.id,
                artifact_type=ArtifactType.ROLLBACK_PLAN,
                title="Rollback plan",
                uri_or_path=f"artifacts/{workitem.id}/rollback-plan.md",
                created_by=role,
            )

    @staticmethod
    def _normalize_modules(modules: list[str]) -> list[str]:
        normalized = []
        for item in modules:
            if not isinstance(item, str):
                raise ValueError("modules must be string values")
            cleaned = item.strip()
            if not cleaned:
                continue
            normalized.append(cleaned)
        unique_modules = list(dict.fromkeys(normalized))
        if not unique_modules:
            raise ValueError("modules must contain at least one non-empty value")
        return unique_modules

    @staticmethod
    def _build_execution_text(workitem: WorkItem) -> str:
        module_label = workitem.module_key or "unknown-module"
        discussion_resolved = bool(workitem.metadata.get("discussion_resolved"))
        return (
            f"role={workitem.role}; module={module_label}; execute stage; "
            f"discussion_resolved={str(discussion_resolved).lower()}"
        )

    def is_terminal(self, run_id: str) -> bool:
        run = self._scheduler.get_run(run_id)
        return run.status in {
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELED,
        }
