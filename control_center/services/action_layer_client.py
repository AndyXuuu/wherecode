from __future__ import annotations

from dataclasses import dataclass

import httpx

from control_center.models.api import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionLayerHealthResponse,
)


@dataclass(slots=True)
class ActionLayerClientError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail


class ActionLayerClient:
    def __init__(self, base_url: str, timeout_seconds: float = 3.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def get_health(self) -> ActionLayerHealthResponse:
        payload = await self._request("GET", "/healthz")
        return ActionLayerHealthResponse(**payload)

    async def execute(self, request: ActionExecuteRequest) -> ActionExecuteResponse:
        payload = await self._request("POST", "/execute", json=request.model_dump())
        return ActionExecuteResponse(**payload)

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.request(method, url, json=json)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ActionLayerClientError("action layer returned unexpected response")
                return payload
        except httpx.HTTPStatusError as exc:
            raise ActionLayerClientError(
                f"action layer request failed: HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ActionLayerClientError(f"action layer unavailable: {exc}") from exc
