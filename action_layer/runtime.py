from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class ActionLayerHandler(BaseHTTPRequestHandler):
    server_version = "WhereCodeActionLayer/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "layer": "action", "transport": "http"},
            )
            return

        if self.path == "/capabilities":
            self._send_json(
                HTTPStatus.OK,
                {
                    "agents": [
                        "coding",
                        "test",
                        "review",
                    ],
                    "status": "stub",
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

        lowered = text.lower()
        if "fail" in lowered or "error" in lowered:
            result = {
                "status": "failed",
                "summary": "action-layer mock execution failed by command content",
                "agent": "coding",
                "trace_id": f"act_{uuid4().hex[:12]}",
            }
        else:
            result = {
                "status": "success",
                "summary": "action-layer mock execution completed",
                "agent": "coding",
                "trace_id": f"act_{uuid4().hex[:12]}",
            }

        self._send_json(HTTPStatus.OK, result)

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
