from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status

from control_center.models import (
    ApproveRollbackApprovalRequest,
    CreateRollbackApprovalRequest,
    ExportRollbackApprovalPurgeAuditsResponse,
    MetricsAlertPolicyAuditEntry,
    MetricsAlertPolicyResponse,
    MetricsAlertPolicyUpdateRequest,
    MetricsSummaryResponse,
    PurgeRollbackApprovalPurgeAuditsRequest,
    PurgeRollbackApprovalPurgeAuditsResponse,
    PurgeRollbackApprovalsAuditEntry,
    PurgeRollbackApprovalsRequest,
    PurgeRollbackApprovalsResponse,
    RollbackApprovalResponse,
    RollbackApprovalStatsResponse,
    RollbackMetricsAlertPolicyRequest,
    RollbackMetricsAlertPolicyResponse,
    VerifyPolicyRegistryAuditEntry,
    VerifyPolicyRegistryExportResponse,
    VerifyPolicyRegistryResponse,
    VerifyPolicyRegistryUpdateRequest,
    WorkflowMetricsResponse,
)
from control_center.models.hierarchy import now_utc
from control_center.services import (
    InMemoryOrchestrator,
    MetricsAlertPolicyStore,
    PolicyRollbackApprovalError,
    PolicyRollbackConflictError,
    WorkflowScheduler,
)


def create_metrics_router(
    *,
    store_provider: Callable[[], InMemoryOrchestrator],
    workflow_scheduler_provider: Callable[[], WorkflowScheduler],
    metrics_alert_policy_store_provider: Callable[[], MetricsAlertPolicyStore],
    authorize_metrics_policy_update: Callable[[Request, str], str],
    authorize_metrics_rollback_approval: Callable[[Request, str], str],
    metrics_rollback_requires_approval: bool | None = None,
    metrics_rollback_requires_approval_provider: Callable[[], bool] | None = None,
) -> APIRouter:
    router = APIRouter()

    def _store() -> InMemoryOrchestrator:
        return store_provider()

    def _workflow_scheduler() -> WorkflowScheduler:
        return workflow_scheduler_provider()

    def _metrics_alert_policy_store() -> MetricsAlertPolicyStore:
        return metrics_alert_policy_store_provider()

    def _metrics_rollback_requires_approval() -> bool:
        if metrics_rollback_requires_approval_provider is not None:
            return metrics_rollback_requires_approval_provider()
        return bool(metrics_rollback_requires_approval)

    @router.get("/metrics/summary", response_model=MetricsSummaryResponse)
    async def get_metrics_summary() -> MetricsSummaryResponse:
        return await _store().get_metrics_summary()

    @router.get("/metrics/workflows", response_model=WorkflowMetricsResponse)
    async def get_workflow_metrics() -> WorkflowMetricsResponse:
        payload = _workflow_scheduler().get_metrics()
        return WorkflowMetricsResponse(**payload)

    @router.get(
        "/metrics/workflows/alert-policy",
        response_model=MetricsAlertPolicyResponse,
    )
    async def get_metrics_alert_policy() -> MetricsAlertPolicyResponse:
        payload = _metrics_alert_policy_store().get_policy()
        return MetricsAlertPolicyResponse(**payload)

    @router.put(
        "/metrics/workflows/alert-policy",
        response_model=MetricsAlertPolicyResponse,
    )
    async def update_metrics_alert_policy(
        request: Request,
        payload: MetricsAlertPolicyUpdateRequest,
    ) -> MetricsAlertPolicyResponse:
        actor = authorize_metrics_policy_update(request, payload.updated_by)
        updated = _metrics_alert_policy_store().update_policy(
            {
                "failed_run_delta_gt": payload.failed_run_delta_gt,
                "failed_run_count_gte": payload.failed_run_count_gte,
                "blocked_run_count_gte": payload.blocked_run_count_gte,
                "waiting_approval_count_gte": payload.waiting_approval_count_gte,
                "in_flight_command_count_gte": payload.in_flight_command_count_gte,
            },
            updated_by=actor,
            reason=payload.reason,
        )
        return MetricsAlertPolicyResponse(**updated)

    @router.get(
        "/metrics/workflows/alert-policy/verify-policy",
        response_model=VerifyPolicyRegistryResponse,
    )
    async def get_metrics_verify_policy_registry() -> VerifyPolicyRegistryResponse:
        payload = _metrics_alert_policy_store().get_verify_policy_registry()
        return VerifyPolicyRegistryResponse(**payload)

    @router.put(
        "/metrics/workflows/alert-policy/verify-policy",
        response_model=VerifyPolicyRegistryResponse,
    )
    async def update_metrics_verify_policy_registry(
        request: Request,
        payload: VerifyPolicyRegistryUpdateRequest,
    ) -> VerifyPolicyRegistryResponse:
        actor = authorize_metrics_policy_update(request, payload.updated_by)
        try:
            updated = _metrics_alert_policy_store().update_verify_policy_registry(
                {
                    "default_profile": payload.default_profile,
                    "profiles": {
                        key: value.model_dump(exclude_none=True)
                        for key, value in payload.profiles.items()
                    },
                },
                updated_by=actor,
                reason=payload.reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return VerifyPolicyRegistryResponse(**updated)

    @router.get(
        "/metrics/workflows/alert-policy/verify-policy/audits",
        response_model=list[VerifyPolicyRegistryAuditEntry],
    )
    async def list_metrics_verify_policy_registry_audits(
        limit: int = 20,
    ) -> list[VerifyPolicyRegistryAuditEntry]:
        entries = _metrics_alert_policy_store().list_verify_policy_registry_audits(limit=limit)
        return [VerifyPolicyRegistryAuditEntry(**item) for item in entries]

    @router.get(
        "/metrics/workflows/alert-policy/verify-policy/export",
        response_model=VerifyPolicyRegistryExportResponse,
    )
    async def export_metrics_verify_policy_registry() -> VerifyPolicyRegistryExportResponse:
        payload = _metrics_alert_policy_store().export_verify_policy_registry()
        return VerifyPolicyRegistryExportResponse(**payload)

    @router.post(
        "/metrics/workflows/alert-policy/rollback-approvals",
        response_model=RollbackApprovalResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_metrics_rollback_approval(
        request: Request,
        payload: CreateRollbackApprovalRequest,
    ) -> RollbackApprovalResponse:
        actor = authorize_metrics_policy_update(request, payload.requested_by)
        try:
            created = _metrics_alert_policy_store().create_rollback_approval(
                audit_id=payload.audit_id,
                requested_by=actor,
                reason=payload.reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return RollbackApprovalResponse(**created)

    @router.get(
        "/metrics/workflows/alert-policy/rollback-approvals",
        response_model=list[RollbackApprovalResponse],
    )
    async def list_metrics_rollback_approvals(
        limit: int = 20,
        status_filter: str | None = None,
    ) -> list[RollbackApprovalResponse]:
        entries = _metrics_alert_policy_store().list_rollback_approvals(
            limit=limit,
            status=status_filter,
        )
        return [RollbackApprovalResponse(**item) for item in entries]

    @router.get(
        "/metrics/workflows/alert-policy/rollback-approvals/stats",
        response_model=RollbackApprovalStatsResponse,
    )
    async def get_metrics_rollback_approval_stats() -> RollbackApprovalStatsResponse:
        payload = _metrics_alert_policy_store().get_rollback_approval_stats()
        return RollbackApprovalStatsResponse(**payload)

    @router.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge",
        response_model=PurgeRollbackApprovalsResponse,
    )
    async def purge_metrics_rollback_approvals(
        request: Request,
        payload: PurgeRollbackApprovalsRequest,
    ) -> PurgeRollbackApprovalsResponse:
        actor = authorize_metrics_policy_update(request, payload.requested_by)
        result = _metrics_alert_policy_store().purge_rollback_approvals(
            remove_used=payload.remove_used,
            remove_expired=payload.remove_expired,
            dry_run=payload.dry_run,
            older_than_seconds=payload.older_than_seconds,
            requested_by=actor,
        )
        return PurgeRollbackApprovalsResponse(
            requested_by=actor,
            dry_run=payload.dry_run,
            remove_used=payload.remove_used,
            remove_expired=payload.remove_expired,
            older_than_seconds=payload.older_than_seconds,
            **result,
        )

    @router.get(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits",
        response_model=list[PurgeRollbackApprovalsAuditEntry],
    )
    async def list_metrics_rollback_approval_purge_audits(
        limit: int = 20,
    ) -> list[PurgeRollbackApprovalsAuditEntry]:
        entries = _metrics_alert_policy_store().list_rollback_approval_purge_audits(limit=limit)
        return [PurgeRollbackApprovalsAuditEntry(**item) for item in entries]

    @router.get(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/export",
        response_model=ExportRollbackApprovalPurgeAuditsResponse,
    )
    async def export_metrics_rollback_approval_purge_audits(
        limit: int = 100,
        event_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> ExportRollbackApprovalPurgeAuditsResponse:
        normalized_limit = max(1, min(limit, 5000))
        entries = _metrics_alert_policy_store().list_rollback_approval_purge_audits(
            limit=normalized_limit,
            event_type=event_type,
            created_after=created_after,
            created_before=created_before,
        )
        normalized_entries = [PurgeRollbackApprovalsAuditEntry(**item) for item in entries]
        digest_payload = [item.model_dump(mode="json") for item in normalized_entries]
        checksum_sha256 = hashlib.sha256(
            json.dumps(digest_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return ExportRollbackApprovalPurgeAuditsResponse(
            exported_total=len(normalized_entries),
            limit=normalized_limit,
            event_type=event_type.strip() if event_type else None,
            created_after=created_after,
            created_before=created_before,
            generated_at=now_utc(),
            checksum_scope="entries",
            checksum_sha256=checksum_sha256,
            entries=normalized_entries,
        )

    @router.post(
        "/metrics/workflows/alert-policy/rollback-approvals/purge-audits/purge",
        response_model=PurgeRollbackApprovalPurgeAuditsResponse,
    )
    async def purge_metrics_rollback_approval_purge_audits(
        request: Request,
        payload: PurgeRollbackApprovalPurgeAuditsRequest,
    ) -> PurgeRollbackApprovalPurgeAuditsResponse:
        actor = authorize_metrics_policy_update(request, payload.requested_by)
        if payload.older_than_seconds is None and payload.keep_latest == 0:
            raise HTTPException(
                status_code=409,
                detail="safety check failed: provide older_than_seconds or keep_latest",
            )
        result = _metrics_alert_policy_store().purge_rollback_approval_purge_audits(
            dry_run=payload.dry_run,
            older_than_seconds=payload.older_than_seconds,
            keep_latest=payload.keep_latest,
            requested_by=actor,
        )
        return PurgeRollbackApprovalPurgeAuditsResponse(
            requested_by=actor,
            dry_run=payload.dry_run,
            older_than_seconds=payload.older_than_seconds,
            keep_latest=payload.keep_latest,
            **result,
        )

    @router.post(
        "/metrics/workflows/alert-policy/rollback-approvals/{approval_id}/approve",
        response_model=RollbackApprovalResponse,
    )
    async def approve_metrics_rollback_approval(
        approval_id: str,
        request: Request,
        payload: ApproveRollbackApprovalRequest,
    ) -> RollbackApprovalResponse:
        actor = authorize_metrics_rollback_approval(request, payload.approved_by)
        try:
            approved = _metrics_alert_policy_store().approve_rollback_approval(
                approval_id,
                approved_by=actor,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PolicyRollbackApprovalError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RollbackApprovalResponse(**approved)

    @router.post(
        "/metrics/workflows/alert-policy/rollback",
        response_model=RollbackMetricsAlertPolicyResponse,
    )
    async def rollback_metrics_alert_policy(
        request: Request,
        payload: RollbackMetricsAlertPolicyRequest,
    ) -> RollbackMetricsAlertPolicyResponse:
        actor = authorize_metrics_policy_update(request, payload.updated_by)
        if _metrics_rollback_requires_approval() and not payload.dry_run:
            approval_id = (payload.approval_id or "").strip()
            if not approval_id:
                raise HTTPException(
                    status_code=409,
                    detail="rollback approval required: approval_id is missing",
                )
        else:
            approval_id = (payload.approval_id or "").strip() or None
        try:
            rolled = _metrics_alert_policy_store().rollback_to_audit(
                payload.audit_id,
                updated_by=actor,
                reason=payload.reason,
                dry_run=payload.dry_run,
                idempotency_key=payload.idempotency_key,
                approval_id=approval_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PolicyRollbackApprovalError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PolicyRollbackConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return RollbackMetricsAlertPolicyResponse(**rolled)

    @router.get(
        "/metrics/workflows/alert-policy/audits",
        response_model=list[MetricsAlertPolicyAuditEntry],
    )
    async def list_metrics_alert_policy_audits(
        limit: int = 20,
    ) -> list[MetricsAlertPolicyAuditEntry]:
        entries = _metrics_alert_policy_store().list_audits(limit=limit)
        normalized: list[MetricsAlertPolicyAuditEntry] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            updated_at = item.get("updated_at")
            if updated_at is None:
                continue
            policy = item.get("policy")
            if not isinstance(policy, dict):
                policy = {}
            entry_id = str(item.get("id", "")).strip()
            if not entry_id:
                continue
            normalized.append(
                MetricsAlertPolicyAuditEntry(
                    id=entry_id,
                    updated_at=updated_at,
                    updated_by=str(item.get("updated_by", "")).strip(),
                    reason=str(item["reason"]) if item.get("reason") is not None else None,
                    rollback_from_audit_id=(
                        str(item["rollback_from_audit_id"])
                        if item.get("rollback_from_audit_id") is not None
                        else None
                    ),
                    rollback_request_id=(
                        str(item["rollback_request_id"])
                        if item.get("rollback_request_id") is not None
                        else None
                    ),
                    rollback_approval_id=(
                        str(item["rollback_approval_id"])
                        if item.get("rollback_approval_id") is not None
                        else None
                    ),
                    policy=policy,
                )
            )
        return normalized

    return router
