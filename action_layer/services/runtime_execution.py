from __future__ import annotations

import os
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from action_layer.services.agent_profile_loader import (
    AgentProfileAccessError,
    AgentProfileLoader,
    AgentProfileNotFoundError,
)
from action_layer.services.agent_registry import AgentRegistry, UnknownAgentRoleError
from action_layer.services.llm_executor import (
    LLMExecutionError,
    LLMRoutingConfig,
    RoutedLLMExecutor,
)


class ActionRuntimeExecutionService:
    def __init__(
        self,
        *,
        registry: AgentRegistry,
        profile_loader: AgentProfileLoader,
        llm_config: LLMRoutingConfig | None,
        llm_executor: RoutedLLMExecutor | None,
        llm_init_error: str | None,
    ) -> None:
        self._registry = registry
        self._profile_loader = profile_loader
        self._llm_config = llm_config
        self._llm_executor = llm_executor
        self._llm_init_error = llm_init_error

    @staticmethod
    def require_llm() -> bool:
        return os.getenv("ACTION_LAYER_REQUIRE_LLM", "true").strip().lower() == "true"

    def execution_mode(self) -> str:
        if self._llm_config is None:
            return "invalid"
        return self._llm_config.mode

    def llm_ready(self) -> bool:
        return self._llm_executor is not None and self._llm_init_error is None

    def provider_name(self) -> str | None:
        if self._llm_config is None or self._llm_config.mode != "llm":
            return None
        if self._llm_executor is None:
            return None
        return self._llm_executor.provider_label()

    def target_names(self) -> list[str]:
        if self._llm_config is None or self._llm_config.mode != "llm":
            return []
        return sorted(self._llm_config.targets.keys())

    def route_summary(self) -> dict[str, object]:
        if self._llm_config is None or self._llm_config.mode != "llm":
            return {}
        return {
            "default": self._llm_config.default_target,
            "by_role": self._llm_config.role_routes,
            "by_module_prefix": self._llm_config.module_prefix_routes,
        }

    def build_health_payload(self) -> dict[str, object]:
        mode = self.execution_mode()
        if self.require_llm() and not self.llm_ready():
            status = "error"
        else:
            status = "ok" if self._llm_init_error is None else "degraded"
        return {
            "status": status,
            "layer": "action",
            "transport": "http",
            "mode": mode,
            "provider": self.provider_name(),
            "llm_targets": self.target_names(),
            "llm_ready": self.llm_ready(),
            "llm_required": self.require_llm(),
            "llm_init_error": self._llm_init_error,
        }

    def build_capabilities_payload(self) -> dict[str, object]:
        mode = self.execution_mode()
        return {
            "agents": sorted(set(self._registry.as_dict().values())),
            "roles": self._registry.list_roles(),
            "status": "llm" if mode == "llm" and self.llm_ready() else "stub",
            "mode": mode,
            "provider": self.provider_name(),
            "llm_targets": self.target_names(),
            "llm_routes": self.route_summary(),
            "llm_ready": self.llm_ready(),
            "llm_required": self.require_llm(),
            "llm_init_error": self._llm_init_error,
        }

    @staticmethod
    def _agent_standard_metadata() -> dict[str, object]:
        return {
            "protocol": "ReAct",
            "version": "1.0",
            "trace_schema": "wherecode://protocols/react_trace/v1",
            "trace_schema_path": "control_center/capabilities/protocols/react_trace_v1.schema.json",
        }

    @staticmethod
    def _build_default_agent_trace(
        *,
        text: str,
        status: str,
        summary: str,
        discussion: dict[str, object] | None,
    ) -> dict[str, object]:
        normalized_status = str(status).strip().lower() or "failed"
        loop_state = {
            "needs_discussion": "needs_discussion",
            "failed": "final",
            "success": "final",
        }.get(normalized_status, "final")
        compact_text = text.strip()
        if len(compact_text) > 180:
            compact_text = f"{compact_text[:177]}..."
        steps: list[dict[str, object]] = [
            {
                "index": 1,
                "phase": "plan",
                "content": compact_text or "execute requested task",
                "status": "ok",
            },
            {
                "index": 2,
                "phase": "act",
                "content": "dispatch action to selected executor",
                "status": "ok",
            },
        ]
        if discussion is not None and normalized_status == "needs_discussion":
            question = str(discussion.get("question") or "").strip()
            steps.append(
                {
                    "index": 3,
                    "phase": "observe",
                    "content": question or "discussion required",
                    "status": "needs_discussion",
                }
            )
        else:
            steps.append(
                {
                    "index": 3,
                    "phase": "observe",
                    "content": summary.strip() or "execution completed",
                    "status": "ok" if normalized_status == "success" else "error",
                }
            )
        return {
            "standard": "ReAct",
            "version": "1.0",
            "loop_state": loop_state,
            "steps": steps,
            "final_decision": normalized_status,
            "truncated": False,
        }

    @staticmethod
    def _sanitize_agent_trace(raw: object) -> dict[str, object] | None:
        if not isinstance(raw, dict):
            return None

        allowed_loop_states = {
            "planning",
            "acting",
            "observing",
            "needs_discussion",
            "final",
        }
        allowed_final_decisions = {"success", "failed", "needs_discussion"}
        allowed_step_phases = {"plan", "act", "observe", "final"}
        allowed_step_statuses = {"ok", "error", "needs_discussion", "skipped"}

        loop_state = str(raw.get("loop_state") or "").strip().lower()
        if loop_state not in allowed_loop_states:
            loop_state = "final"
        final_decision = str(raw.get("final_decision") or "").strip().lower()
        if final_decision not in allowed_final_decisions:
            final_decision = "failed"
        standard = str(raw.get("standard") or "ReAct").strip() or "ReAct"
        version = str(raw.get("version") or "1.0").strip() or "1.0"
        truncated = bool(raw.get("truncated", False))

        sanitized_steps: list[dict[str, object]] = []
        raw_steps = raw.get("steps")
        if isinstance(raw_steps, list):
            for idx, item in enumerate(raw_steps, start=1):
                if not isinstance(item, dict):
                    continue
                phase = str(item.get("phase") or "").strip()
                content = str(item.get("content") or "").strip()
                if not phase and not content:
                    continue
                normalized_phase = phase.lower()
                if normalized_phase not in allowed_step_phases:
                    continue
                status = str(item.get("status") or "").strip().lower()
                if status and status not in allowed_step_statuses:
                    status = ""
                tool = str(item.get("tool") or "").strip()
                sanitized_steps.append(
                    {
                        "index": idx,
                        "phase": normalized_phase,
                        "content": content,
                        "tool": tool,
                        "status": status,
                    }
                )
                if len(sanitized_steps) >= 12:
                    truncated = True
                    break

        return {
            "standard": standard,
            "version": version,
            "loop_state": loop_state,
            "steps": sanitized_steps,
            "final_decision": final_decision,
            "truncated": truncated,
        }

    def _with_standard_agent_contract(
        self,
        result: dict[str, object],
        *,
        text: str,
    ) -> dict[str, object]:
        payload = dict(result)
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["agent_standard"] = self._agent_standard_metadata()
        payload["metadata"] = metadata

        status = str(payload.get("status") or "").strip().lower()
        summary = str(payload.get("summary") or "")
        discussion = payload.get("discussion")
        discussion_obj = discussion if isinstance(discussion, dict) else None
        trace = self._sanitize_agent_trace(payload.get("agent_trace"))
        if trace is None:
            trace = self._build_default_agent_trace(
                text=text,
                status=status,
                summary=summary,
                discussion=discussion_obj,
            )
        payload["agent_trace"] = trace
        return payload

    def execute(self, payload: dict[str, object]) -> tuple[HTTPStatus, dict[str, object]]:
        text = str(payload.get("text", "")).strip()
        if not text:
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "detail": "text must be a non-empty string"
            }

        requested_role = str(payload.get("role", "")).strip().lower()
        requested_agent = str(payload.get("agent", "")).strip()
        profile_hash = None
        resolved_role = None

        if requested_role:
            try:
                profile = self._profile_loader.load(requested_role)
                profile_hash = profile.profile_hash
                resolved_role = profile.role
            except (AgentProfileAccessError, AgentProfileNotFoundError) as exc:
                return HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": str(exc)}

            if not requested_agent:
                try:
                    requested_agent = self._registry.resolve(requested_role)
                except UnknownAgentRoleError as exc:
                    return HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": str(exc)}

        if not requested_agent:
            requested_agent = "coding-agent"
        payload["agent"] = requested_agent

        base_metadata: dict[str, object] = {
            "role": resolved_role,
            "profile_hash": profile_hash,
            "execution_mode": self.execution_mode(),
        }

        lowered = text.lower()
        if (
            "role=module-dev" in lowered
            and "module=needs-discussion" in lowered
            and "discussion_resolved=true" not in lowered
        ):
            result = {
                "status": "needs_discussion",
                "summary": "need discussion before implementation",
                "agent": requested_agent,
                "trace_id": f"act_{uuid4().hex[:12]}",
                "discussion": {
                    "question": "Pick implementation strategy",
                    "options": ["option-a", "option-b"],
                    "recommendation": "option-a",
                    "impact": "changes module behavior",
                    "fingerprint": "needs-discussion-module-dev",
                },
                "metadata": base_metadata,
            }
            return HTTPStatus.OK, self._with_standard_agent_contract(result, text=text)

        if self.execution_mode() == "llm" and self.llm_ready():
            result = self._execute_with_llm(payload, base_metadata)
            return HTTPStatus.OK, self._with_standard_agent_contract(result, text=text)
        if self.require_llm():
            return HTTPStatus.SERVICE_UNAVAILABLE, {
                "detail": "llm execution is required but not ready",
                "mode": self.execution_mode(),
                "llm_init_error": self._llm_init_error,
            }
        result = self._execute_mock(text, requested_agent, base_metadata)
        return HTTPStatus.OK, self._with_standard_agent_contract(result, text=text)

    def _execute_with_llm(
        self,
        payload: dict[str, object],
        base_metadata: dict[str, object],
    ) -> dict[str, object]:
        if self._llm_executor is None:
            failed_metadata = dict(base_metadata)
            failed_metadata["llm_error"] = "llm executor not initialized"
            return {
                "status": "failed",
                "summary": "llm execution unavailable",
                "agent": str(payload.get("agent", "")).strip() or "coding-agent",
                "trace_id": f"act_{uuid4().hex[:12]}",
                "metadata": failed_metadata,
            }

        try:
            result = self._llm_executor.execute(payload)
        except LLMExecutionError as exc:
            failed_metadata = dict(base_metadata)
            failed_metadata["llm_error"] = str(exc)
            return {
                "status": "failed",
                "summary": "llm execution failed",
                "agent": str(payload.get("agent", "")).strip() or "coding-agent",
                "trace_id": f"act_{uuid4().hex[:12]}",
                "metadata": failed_metadata,
            }

        merged_metadata = dict(base_metadata)
        raw_metadata = result.get("metadata")
        if isinstance(raw_metadata, dict):
            merged_metadata.update(raw_metadata)
        result["metadata"] = merged_metadata

        status = str(result.get("status", "")).strip().lower()
        if status not in {"success", "failed", "needs_discussion"}:
            result["status"] = "failed"
            result["summary"] = "llm response returned invalid status"
            merged_metadata["llm_error"] = "invalid_status"

        if not isinstance(result.get("summary"), str) or not str(result["summary"]).strip():
            result["summary"] = "llm execution completed"
        if not isinstance(result.get("trace_id"), str) or not str(result["trace_id"]).strip():
            result["trace_id"] = f"act_{uuid4().hex[:12]}"
        if not isinstance(result.get("agent"), str) or not str(result["agent"]).strip():
            result["agent"] = str(payload.get("agent", "")).strip() or "coding-agent"
        return result

    @staticmethod
    def _execute_mock(
        text: str,
        requested_agent: str,
        base_metadata: dict[str, object],
    ) -> dict[str, object]:
        lowered = text.lower()
        if "fail" in lowered or "error" in lowered:
            return {
                "status": "failed",
                "summary": "mock execution failed by command content",
                "agent": requested_agent,
                "trace_id": f"act_{uuid4().hex[:12]}",
                "metadata": base_metadata,
            }
        return {
            "status": "success",
            "summary": "mock execution completed",
            "agent": requested_agent,
            "trace_id": f"act_{uuid4().hex[:12]}",
            "metadata": base_metadata,
        }
