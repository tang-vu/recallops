"""Domain models shared by the memory and policy boundaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[Decimal, Field(ge=Decimal("0"), max_digits=24, decimal_places=6)]


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


class StrictModel(BaseModel):
    """Reject unknown input so policy fields cannot be smuggled past validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Decision(StrEnum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class MemoryTier(StrEnum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    REFERENCE = "REFERENCE"
    ARCHIVE = "ARCHIVE"


class OwnerPolicy(StrictModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    owner_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    currency: str = Field(default="USDC", pattern=r"^[A-Z0-9]{2,12}$")
    chain: str = Field(default="base-sepolia", max_length=64)
    per_action_limit: Money
    cumulative_budget: Money
    window_started_at: datetime
    window_ends_at: datetime
    require_verifier: bool = True
    high_risk_requires_human: bool = True


class BudgetAccount(StrictModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    owner_id: str = Field(min_length=1, max_length=128)
    currency: str = Field(pattern=r"^[A-Z0-9]{2,12}$")
    spent: Money = Decimal("0")
    window_started_at: datetime
    window_ends_at: datetime
    source_session_id: UUID
    updated_at: datetime = Field(default_factory=utc_now)


class FailureFingerprint(StrictModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    provider_id: str = Field(min_length=1, max_length=128)
    task_category: str = Field(min_length=1, max_length=128)
    task_fingerprint: str = Field(min_length=1, max_length=256)
    verifier_id: str = Field(min_length=1, max_length=128)
    verification_reason: str = Field(min_length=1, max_length=512)
    source_session_id: UUID
    job_reference: str | None = Field(default=None, max_length=256)
    failed_at: datetime = Field(default_factory=utc_now)
    active: bool = True


class ProposedAction(StrictModel):
    action_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1, max_length=128)
    owner_id: str = Field(min_length=1, max_length=128)
    requesting_agent_id: str = Field(min_length=1, max_length=128)
    provider_id: str = Field(min_length=1, max_length=128)
    offering: str = Field(min_length=1, max_length=256)
    task_category: str = Field(min_length=1, max_length=128)
    task_fingerprint: str = Field(min_length=1, max_length=256)
    requested_amount: Money
    currency: str = Field(pattern=r"^[A-Z0-9]{2,12}$")
    chain: str = Field(min_length=1, max_length=64)
    session_id: UUID
    required_verifier: str | None = Field(default=None, max_length=128)
    risk_class: str = Field(default="LOW", pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
    permission: str = Field(min_length=1, max_length=128)
    proposed_at: datetime = Field(default_factory=utc_now)
    rationale: str | None = Field(default=None, max_length=2_000)


class StoredMemory(StrictModel):
    tier: MemoryTier
    record_type: str
    record_name: str
    body: dict[str, Any]
    written_at: datetime
    source_session_id: UUID | None = None
    status: str = "active"


class MemoryEvidence(StrictModel):
    tier: MemoryTier
    record_type: str
    record_name: str
    source_session_id: UUID | None = None
    written_at: datetime
    recalled_at: datetime
    why_it_mattered: str
    status: str
    content: dict[str, Any]
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvaluationContext(StrictModel):
    policy: StoredMemory | None
    budget: StoredMemory | None
    matching_failure: StoredMemory | None


class DecisionReceipt(StrictModel):
    receipt_id: UUID = Field(default_factory=uuid4)
    decision: Decision
    action_id: UUID
    tenant_id: str
    session_id: UUID
    policy_version: str
    reason_codes: tuple[str, ...]
    human_summary: str
    memory_evidence: tuple[MemoryEvidence, ...]
    budget_before: Money
    budget_after_if_approved: Money
    counterparty_risk: dict[str, Any]
    memory_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=lambda: utc_now() + timedelta(minutes=5))
    virtuals_job_id: str | None = None
    base_transaction_hash: str | None = None
