"""Policy and verification gate for tamper-evident Base receipt anchoring."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from recallops.integrations.base import BaseAnchorRequest, BaseAnchorResult, BasePort
from recallops.models import (
    BaseAnchorRecord,
    Decision,
    DecisionReceipt,
    ExecutionAuthorization,
    ExecutionStatus,
    JobRecord,
    JobStatus,
)
from recallops.orchestration.execution import request_digest


class BaseAnchorBlockedError(RuntimeError):
    """Durable policy or verification state does not permit an anchor transaction."""


class BaseAnchorMemory(Protocol):
    def get_decision(self, receipt_id: str) -> DecisionReceipt | None: ...

    def get_execution_authorization(self, receipt_id: str) -> ExecutionAuthorization | None: ...

    def get_job(self, job_id: str) -> JobRecord | None: ...

    def get_base_anchor(self, receipt_id: str) -> BaseAnchorRecord | None: ...

    def write_base_anchor(self, anchor: BaseAnchorRecord) -> list[dict[str, str]]: ...


class BaseAnchorOrchestrator:
    """Anchor only a passed, approval-bound commerce result."""

    def __init__(self, adapter: BasePort) -> None:
        self._adapter = adapter

    def anchor(
        self, *, memory: BaseAnchorMemory, receipt_id: UUID, action_id: UUID
    ) -> tuple[BaseAnchorRecord, tuple[dict[str, str], ...], bool]:
        receipt = memory.get_decision(str(receipt_id))
        authorization = memory.get_execution_authorization(str(receipt_id))
        existing = memory.get_base_anchor(str(receipt_id))
        if existing is not None:
            if existing.action_id != action_id:
                raise BaseAnchorBlockedError("The persisted anchor belongs to a different action")
            if receipt is None or authorization is None:
                raise BaseAnchorBlockedError("The persisted anchor has incomplete durable state")
            if (
                receipt.base_transaction_hash == existing.transaction_hash
                and authorization.base_transaction_hash == existing.transaction_hash
            ):
                return existing, (), True
            writes = memory.write_base_anchor(existing)
            return existing, tuple(writes), True

        if receipt is None or receipt.action_id != action_id:
            raise BaseAnchorBlockedError("A matching durable decision receipt is required")
        if receipt.decision is not Decision.APPROVE:
            raise BaseAnchorBlockedError("Only an APPROVE receipt can anchor an execution result")
        if authorization is None or authorization.action_id != action_id:
            raise BaseAnchorBlockedError("A matching durable execution authorization is required")
        if authorization.status is not ExecutionStatus.SUCCEEDED:
            raise BaseAnchorBlockedError("Execution must succeed before Base anchoring")
        if authorization.virtuals_job_id is None:
            raise BaseAnchorBlockedError("A durable ACP job reference is required before anchoring")
        job = memory.get_job(authorization.virtuals_job_id)
        allowed_states = {
            JobStatus.VERIFIED_PASSED,
            JobStatus.PAYMENT_AUTHORIZED,
            JobStatus.COMPLETED,
        }
        if job is None or job.receipt_id != receipt_id or job.status not in allowed_states:
            raise BaseAnchorBlockedError("The ACP result must pass verification before anchoring")
        if self._adapter.mode == "BASE SEPOLIA" and job.integration_mode != "LIVE VIRTUALS":
            raise BaseAnchorBlockedError("Fixture ACP jobs cannot produce live Base evidence")

        digest = "0x" + request_digest(
            receipt.model_dump(mode="json", exclude={"base_transaction_hash"})
        )
        result: BaseAnchorResult = self._adapter.anchor(
            BaseAnchorRequest(
                tenant_id=receipt.tenant_id,
                receipt_id=receipt.receipt_id,
                action_id=receipt.action_id,
                decision=receipt.decision,
                decision_digest=digest,
                acp_job_reference=authorization.virtuals_job_id,
            )
        )
        if not result.verified or result.chain_id != self._adapter.chain_id:
            raise BaseAnchorBlockedError("The Base transaction could not be verified")
        anchor = BaseAnchorRecord(
            tenant_id=receipt.tenant_id,
            receipt_id=receipt.receipt_id,
            action_id=receipt.action_id,
            chain_id=result.chain_id,
            contract_address=result.contract_address,
            transaction_hash=result.transaction_hash,
            receipt_id_digest=result.receipt_id_digest,
            decision_digest=result.decision_digest,
            acp_job_reference_digest=result.acp_job_reference_digest,
            record_hash=result.record_hash,
            explorer_url=result.explorer_url,
            integration_mode=self._adapter.mode,
        )
        writes = memory.write_base_anchor(anchor)
        return anchor, tuple(writes), not result.created
