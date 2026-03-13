from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from action_layer.services import (
    ActionRuntimeExecutionService,
    AgentProfileLoader,
    AgentRegistry,
    LLMConfigurationError,
    LLMRoutingConfig,
    RoutedLLMExecutor,
)
from action_layer.services.agent_rules_registry_loader import (
    build_registry_mapping_with_fallback,
)


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class ActionLayerHandler(BaseHTTPRequestHandler):
    server_version = "WhereCodeActionLayer/0.1"
    registry = AgentRegistry(
        mapping=build_registry_mapping_with_fallback(
            os.getenv(
                "ACTION_LAYER_AGENT_RULES_REGISTRY_FILE",
                "control_center/capabilities/agent_rules_registry.json",
            ),
            scope_order=os.getenv("ACTION_LAYER_AGENT_RULES_SCOPES", "subproject,main"),
            fallback_mapping=AgentRegistry.default_mapping(),
        )
    )
    profile_loader = AgentProfileLoader(
        os.getenv(
            "ACTION_LAYER_AGENT_PROFILES_ROOT",
            ".agents/roles:action_layer/agents",
        )
    )
    try:
        llm_config = LLMRoutingConfig.from_env()
        llm_executor = (
            RoutedLLMExecutor(llm_config) if llm_config.mode == "llm" else None
        )
        llm_init_error = None
    except LLMConfigurationError as exc:
        llm_config = None
        llm_executor = None
        llm_init_error = str(exc)

    execution_service = ActionRuntimeExecutionService(
        registry=registry,
        profile_loader=profile_loader,
        llm_config=llm_config,
        llm_executor=llm_executor,
        llm_init_error=llm_init_error,
    )

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._send_json(
                HTTPStatus.OK,
                self.execution_service.build_health_payload(),
            )
            return

        if self.path == "/capabilities":
            self._send_json(
                HTTPStatus.OK,
                self.execution_service.build_capabilities_payload(),
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/execute":
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})
            return

        payload = self._read_json_body()
        if payload is None:
            return

        status_code, response_payload = self.execution_service.execute(payload)
        self._send_json(status_code, response_payload)

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
    if ActionLayerHandler.execution_service.require_llm() and not ActionLayerHandler.execution_service.llm_ready():
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
