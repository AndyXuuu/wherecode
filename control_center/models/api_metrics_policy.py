from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MetricsAlertPolicy(BaseModel):
    failed_run_delta_gt: int = Field(default=0, ge=0)
    failed_run_count_gte: int = Field(default=1, ge=0)
    blocked_run_count_gte: int = Field(default=2, ge=0)
    waiting_approval_count_gte: int = Field(default=10, ge=0)
    in_flight_command_count_gte: int = Field(default=50, ge=0)


class MetricsAlertPolicyUpdateRequest(MetricsAlertPolicy):
    updated_by: str = Field(min_length=1)
    reason: str | None = None


class MetricsAlertPolicyResponse(MetricsAlertPolicy):
    policy_path: str
    updated_at: datetime
    audit_count: int = Field(default=0, ge=0)


class MetricsAlertPolicyAuditEntry(BaseModel):
    id: str
    updated_at: datetime
    updated_by: str
    reason: str | None = None
    rollback_from_audit_id: str | None = None
    rollback_request_id: str | None = None
    rollback_approval_id: str | None = None
    policy: MetricsAlertPolicy


class VerifyPolicyProfileConfig(BaseModel):
    allowed_resolvers: list[str] | None = None
    preflight_slo_min_pass_rate: float | None = Field(default=None, ge=0, le=1)
    preflight_slo_max_consecutive_failures: int | None = Field(default=None, ge=0)
    verify_slo_min_pass_rate: float | None = Field(default=None, ge=0, le=1)
    verify_slo_max_fetch_failures: int | None = Field(default=None, ge=0)


class VerifyPolicyRegistryResponse(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, VerifyPolicyProfileConfig] = Field(default_factory=dict)
    registry_path: str
    updated_at: datetime
    audit_count: int = Field(default=0, ge=0)


class VerifyPolicyRegistryUpdateRequest(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, VerifyPolicyProfileConfig] = Field(default_factory=dict)
    updated_by: str = Field(min_length=1)
    reason: str | None = None


class VerifyPolicyRegistryAuditEntry(BaseModel):
    id: str
    updated_at: datetime
    updated_by: str
    reason: str | None = None
    registry: dict[str, object]


class VerifyPolicyRegistryExportResponse(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, VerifyPolicyProfileConfig] = Field(default_factory=dict)
    generated_at: datetime
    source: str


class RollbackMetricsAlertPolicyRequest(BaseModel):
    audit_id: str = Field(min_length=1)
    updated_by: str = Field(min_length=1)
    reason: str | None = None
    dry_run: bool = False
    idempotency_key: str | None = None
    approval_id: str | None = None


class RollbackMetricsAlertPolicyResponse(BaseModel):
    source_audit_id: str
    dry_run: bool
    applied: bool
    idempotent_replay: bool = False
    policy: MetricsAlertPolicy
    policy_path: str
    audit_count: int = Field(default=0, ge=0)


class RollbackApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    USED = "used"
    EXPIRED = "expired"


class CreateRollbackApprovalRequest(BaseModel):
    audit_id: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    reason: str | None = None


class ApproveRollbackApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=1)


class RollbackApprovalResponse(BaseModel):
    id: str
    audit_id: str
    status: RollbackApprovalStatus
    requested_by: str
    approved_by: str | None = None
    used_by: str | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class RollbackApprovalStatsResponse(BaseModel):
    total: int = Field(default=0, ge=0)
    pending: int = Field(default=0, ge=0)
    approved: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    used: int = Field(default=0, ge=0)
    expired: int = Field(default=0, ge=0)


class PurgeRollbackApprovalsRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    remove_used: bool = True
    remove_expired: bool = True
    dry_run: bool = False
    older_than_seconds: int | None = Field(default=None, ge=0)


class PurgeRollbackApprovalsResponse(BaseModel):
    requested_by: str
    dry_run: bool
    remove_used: bool
    remove_expired: bool
    older_than_seconds: int | None = Field(default=None, ge=0)
    purge_audit_id: str | None = None
    removed_used: int = Field(default=0, ge=0)
    removed_expired: int = Field(default=0, ge=0)
    removed_total: int = Field(default=0, ge=0)
    remaining_total: int = Field(default=0, ge=0)


class PurgeRollbackApprovalsAuditEntry(BaseModel):
    id: str
    event_type: str = "approval_purge"
    requested_by: str
    dry_run: bool
    remove_used: bool | None = None
    remove_expired: bool | None = None
    older_than_seconds: int | None = Field(default=None, ge=0)
    keep_latest: int | None = Field(default=None, ge=0)
    removed_used: int = Field(default=0, ge=0)
    removed_expired: int = Field(default=0, ge=0)
    removed_total: int = Field(default=0, ge=0)
    remaining_total: int = Field(default=0, ge=0)
    created_at: datetime


class PurgeRollbackApprovalPurgeAuditsRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    dry_run: bool = False
    older_than_seconds: int | None = Field(default=None, ge=0)
    keep_latest: int = Field(default=0, ge=0)


class PurgeRollbackApprovalPurgeAuditsResponse(BaseModel):
    requested_by: str
    dry_run: bool
    older_than_seconds: int | None = Field(default=None, ge=0)
    keep_latest: int = Field(default=0, ge=0)
    purge_audit_gc_id: str | None = None
    removed_total: int = Field(default=0, ge=0)
    remaining_total: int = Field(default=0, ge=0)


class ExportRollbackApprovalPurgeAuditsResponse(BaseModel):
    exported_total: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1)
    event_type: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    generated_at: datetime
    checksum_scope: str = "entries"
    checksum_sha256: str
    entries: list[PurgeRollbackApprovalsAuditEntry] = Field(default_factory=list)
