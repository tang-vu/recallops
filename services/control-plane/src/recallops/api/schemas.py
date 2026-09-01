"""HTTP request and response models."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from recallops.models import (
    BudgetAccount,
    DecisionReceipt,
    ExecutionAuthorization,
    HumanApproval,
    HumanException,
    JobRecord,
    OwnerPolicy,
    PermissionGrant,
    StrictModel,
)


class PolicyWriteRequest(StrictModel):
    policy: OwnerPolicy
    source_session_id: UUID


class BudgetWriteRequest(StrictModel):
    budget: BudgetAccount


class PermissionWriteRequest(StrictModel):
    permission: PermissionGrant


class ExceptionWriteRequest(StrictModel):
    exception: HumanException


class ApprovalWriteRequest(StrictModel):
    approval: HumanApproval


class MemoryWriteResponse(StrictModel):
    writes: tuple[dict[str, str], ...]


class EvaluationResponse(StrictModel):
    receipt: DecisionReceipt
    writes: tuple[dict[str, str], ...]
    idempotent_replay: bool = False


class ExecutionRequest(StrictModel):
    receipt_id: UUID
    adapter_payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionAuthorizationResponse(StrictModel):
    authorization: ExecutionAuthorization
    writes: tuple[dict[str, str], ...]
    idempotent_replay: bool
    executor_status: str = "NOT_DISPATCHED"
    note: str = "Authorization is durable; a live adapter is not configured in Milestone 2."


class SystemStatusResponse(StrictModel):
    service: str = "recallops-control-plane"
    version: str
    memory_configured: bool
    memory_healthy: bool
    memory_path_hint: str | None
    virtuals_mode: str
    base_mode: str
    base_chain_id: int
    fixture_data: bool


class BenchmarkUnavailable(StrictModel):
    available: bool = False
    reason: str = "No benchmark run has been persisted yet."


class CounterpartyResponse(StrictModel):
    provider_id: str
    task_category: str
    failed_jobs: int = 0
    successful_jobs: int = 0
    last_failure_fingerprint: str | None = None
    probation_status: str | None = None
    updated_at: str
    status: str


class DemoProcessResponse(StrictModel):
    result: dict[str, Any]


class BudgetSummary(StrictModel):
    spent: Decimal
    limit: Decimal
    remaining: Decimal


class JobWriteRequest(StrictModel):
    job: JobRecord


class JobCallbackRequest(StrictModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    callback_id: str = Field(min_length=8, max_length=256)


class JobVerificationRequest(JobCallbackRequest):
    outcome: str = Field(pattern=r"^(PASSED|FAILED)$")
    verifier_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)
    source_session_id: UUID


class JobResponse(StrictModel):
    job: JobRecord
    writes: tuple[dict[str, str], ...]
    duplicate_callback: bool = False
