from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

from action_layer.services import (
    AgentProfileAccessError,
    AgentProfileLoader,
    AgentProfileNotFoundError,
    AgentRegistry,
    LLMConfigurationError,
    LLMExecutionError,
    LLMRoutingConfig,
    RoutedLLMExecutor,
    UnknownAgentRoleError,
)


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class ActionLayerHandler(BaseHTTPRequestHandler):
    server_version = "WhereCodeActionLayer/0.1"
    registry = AgentRegistry()
    profile_loader = AgentProfileLoader(
        os.getenv("ACTION_LAYER_AGENT_PROFILES_ROOT", "action_layer/agents")
    )
    try:
        llm_config = LLMRoutingConfig.from_env()
        llm_executor = (
            RoutedLLMExecutor(llm_config)
            if llm_config.mode == "llm"
            else None
        )
        llm_init_error = None
    except LLMConfigurationError as exc:
        llm_config = None
        llm_executor = None
        llm_init_error = str(exc)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            mode = self._execution_mode()
            if self._require_llm() and not self._llm_ready():
                status = "error"
            else:
                status = "ok" if self.llm_init_error is None else "degraded"
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": status,
                    "layer": "action",
                    "transport": "http",
                    "mode": mode,
                    "provider": self._provider_name(),
                    "llm_targets": self._target_names(),
                    "llm_ready": self._llm_ready(),
                    "llm_required": self._require_llm(),
                    "llm_init_error": self.llm_init_error,
                },
            )
            return

        if self.path == "/capabilities":
            mode = self._execution_mode()
            self._send_json(
                HTTPStatus.OK,
                {
                    "agents": sorted(set(self.registry.as_dict().values())),
                    "roles": self.registry.list_roles(),
                    "status": "llm" if mode == "llm" and self._llm_ready() else "stub",
                    "mode": mode,
                    "provider": self._provider_name(),
                    "llm_targets": self._target_names(),
                    "llm_routes": self._route_summary(),
                    "llm_ready": self._llm_ready(),
                    "llm_required": self._require_llm(),
                    "llm_init_error": self.llm_init_error,
                },
            )
            return

        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"detail": "not found"},
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/execute":
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})
            return

        payload = self._read_json_body()
        if payload is None:
            return

        text = str(payload.get("text", "")).strip()
        if not text:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"detail": "text must be a non-empty string"},
            )
            return

        requested_role = str(payload.get("role", "")).strip().lower()
        requested_agent = str(payload.get("agent", "")).strip()
        profile_hash = None
        resolved_role = None

        if requested_role:
            try:
                profile = self.profile_loader.load(requested_role)
                profile_hash = profile.profile_hash
                resolved_role = profile.role
            except (AgentProfileAccessError, AgentProfileNotFoundError) as exc:
                self._send_json(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    {"detail": str(exc)},
                )
                return

            if not requested_agent:
                try:
                    requested_agent = self.registry.resolve(requested_role)
                except UnknownAgentRoleError as exc:
                    self._send_json(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        {"detail": str(exc)},
                    )
                    return

        if not requested_agent:
            requested_agent = "coding-agent"
        payload["agent"] = requested_agent

        base_metadata: dict[str, object] = {
            "role": resolved_role,
            "profile_hash": profile_hash,
            "execution_mode": self._execution_mode(),
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
            self._send_json(HTTPStatus.OK, result)
            return

        if self._execution_mode() == "llm" and self._llm_ready():
            result = self._execute_with_llm(payload, base_metadata)
        elif self._require_llm():
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "detail": "llm execution is required but not ready",
                    "mode": self._execution_mode(),
                    "llm_init_error": self.llm_init_error,
                },
            )
            return
        else:
            result = self._execute_mock(text, requested_agent, base_metadata)

        self._send_json(HTTPStatus.OK, result)

    @classmethod
    def _execution_mode(cls) -> str:
        if cls.llm_config is None:
            return "invalid"
        return cls.llm_config.mode

    @staticmethod
    def _require_llm() -> bool:
        return os.getenv("ACTION_LAYER_REQUIRE_LLM", "true").strip().lower() == "true"

    @classmethod
    def _provider_name(cls) -> str | None:
        if cls.llm_config is None or cls.llm_config.mode != "llm":
            return None
        if cls.llm_executor is None:
            return None
        return cls.llm_executor.provider_label()

    @classmethod
    def _target_names(cls) -> list[str]:
        if cls.llm_config is None or cls.llm_config.mode != "llm":
            return []
        return sorted(cls.llm_config.targets.keys())

    @classmethod
    def _route_summary(cls) -> dict[str, object]:
        if cls.llm_config is None or cls.llm_config.mode != "llm":
            return {}
        return {
            "default": cls.llm_config.default_target,
            "by_role": cls.llm_config.role_routes,
            "by_module_prefix": cls.llm_config.module_prefix_routes,
        }

    @classmethod
    def _llm_ready(cls) -> bool:
        return cls.llm_executor is not None and cls.llm_init_error is None

    def _execute_with_llm(
        self,
        payload: dict[str, object],
        base_metadata: dict[str, object],
    ) -> dict[str, object]:
        if self.llm_executor is None:
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
            result = self.llm_executor.execute(payload)
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

    def _execute_mock(
        self,
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

    def _read_json_body(self) -> dict[str, object] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._send_json(HTTPStatus.BAD_REQUEST, {"detail": "empty request body"})
            return None

        body = self.rfile.read(content_length)
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"detail": "invalid json body"})
            return None

        if not isinstance(data, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"detail": "json body must be an object"})
            return None
        return data

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = _json_bytes(payload)
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[action-layer] {self.address_string()} - {fmt % args}")


def main() -> None:
    if ActionLayerHandler._require_llm() and not ActionLayerHandler._llm_ready():
        detail = ActionLayerHandler.llm_init_error or "llm provider is not configured"
        print(f"[action-layer] startup blocked: {detail}")
        raise SystemExit(2)

    host = os.getenv("ACTION_LAYER_HOST", "127.0.0.1")
    port = int(os.getenv("ACTION_LAYER_PORT", "8100"))
    server = ThreadingHTTPServer((host, port), ActionLayerHandler)
    print(f"[action-layer] listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[action-layer] stopped")


if __name__ == "__main__":
    main()
