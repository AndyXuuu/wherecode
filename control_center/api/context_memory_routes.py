from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from control_center.models import (
    ContextMemoryDeleteResponse,
    ContextMemoryItemResponse,
    ContextMemoryResolveResponse,
    ContextMemoryUpsertRequest,
    MemoryNamespaceScope,
)
from control_center.services.context_memory_store import ContextMemoryStore


def create_context_memory_router(
    *,
    context_memory_store_provider: Callable[[], ContextMemoryStore],
) -> APIRouter:
    router = APIRouter()

    def _store() -> ContextMemoryStore:
        return context_memory_store_provider()

    @router.put("/context/memory/items", response_model=ContextMemoryItemResponse)
    async def upsert_context_memory_item(
        payload: ContextMemoryUpsertRequest,
    ) -> ContextMemoryItemResponse:
        try:
            record = _store().upsert(
                scope=payload.scope,
                key=payload.key,
                value=payload.value,
                updated_by=payload.updated_by,
                project_id=payload.project_id,
                run_id=payload.run_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return ContextMemoryItemResponse(**record)

    @router.get("/context/memory/items", response_model=ContextMemoryItemResponse)
    async def get_context_memory_item(
        scope: MemoryNamespaceScope,
        key: str,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> ContextMemoryItemResponse:
        try:
            record = _store().get(
                scope=scope,
                key=key,
                project_id=project_id,
                run_id=run_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if record is None:
            raise HTTPException(status_code=404, detail="context memory item not found")
        return ContextMemoryItemResponse(**record)

    @router.get(
        "/context/memory/namespaces/{scope}/items",
        response_model=list[ContextMemoryItemResponse],
    )
    async def list_context_memory_namespace_items(
        scope: MemoryNamespaceScope,
        project_id: str | None = None,
        run_id: str | None = None,
        prefix: str | None = None,
        limit: int = 200,
    ) -> list[ContextMemoryItemResponse]:
        try:
            records = _store().list_namespace(
                scope=scope,
                project_id=project_id,
                run_id=run_id,
                prefix=prefix,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return [ContextMemoryItemResponse(**item) for item in records]

    @router.delete("/context/memory/items", response_model=ContextMemoryDeleteResponse)
    async def delete_context_memory_item(
        scope: MemoryNamespaceScope,
        key: str,
        project_id: str | None = None,
        run_id: str | None = None,
        deleted_by: str = "system",
    ) -> ContextMemoryDeleteResponse:
        try:
            namespace_id = _store().resolve_namespace_id(
                scope=scope,
                project_id=project_id,
                run_id=run_id,
            )
            deleted, deleted_at = _store().delete(
                scope=scope,
                key=key,
                project_id=project_id,
                run_id=run_id,
                deleted_by=deleted_by,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return ContextMemoryDeleteResponse(
            deleted=deleted,
            scope=scope,
            namespace_id=namespace_id,
            key=key,
            deleted_at=deleted_at,
        )

    @router.get("/context/memory/resolve", response_model=ContextMemoryResolveResponse)
    async def resolve_context_memory(
        project_id: str | None = None,
        run_id: str | None = None,
        keys: list[str] | None = None,
    ) -> ContextMemoryResolveResponse:
        try:
            payload = _store().resolve(
                project_id=project_id,
                run_id=run_id,
                keys=keys,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return ContextMemoryResolveResponse(**payload)

    return router
