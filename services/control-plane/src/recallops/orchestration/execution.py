"""Durable authorization gate for downstream economic executors."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from recallops.memory.port import MemoryPort
from recallops.models import Decision, ExecutionAuthorization


class ExecutionGateError(RuntimeError):
    """Base class for safe execution authorization failures."""


class ReceiptNotFoundError(ExecutionGateError):
    pass


class ExecutionDeniedError(ExecutionGateError):
    pass


class ReceiptExpiredError(ExecutionGateError):
    pass


class ReplayConflictError(ExecutionGateError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def request_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_text(payload)


class ExecutionGate:
    """Authorize an adapter call only after a valid durable decision."""

    def __init__(self, memory: MemoryPort) -> None:
        self._memory = memory

    def authorize(
        self,
        *,
        receipt_id: UUID,
        action_id: UUID,
        idempotency_key: str,
        request_body_digest: str,
        now: datetime | None = None,
    ) -> tuple[ExecutionAuthorization, bool, list[dict[str, str]]]:
        current = now or datetime.now(UTC)
        receipt = self._memory.get_decision(str(receipt_id))
        if receipt is None:
            raise ReceiptNotFoundError("Decision receipt does not exist")
        if receipt.action_id != action_id:
            raise ReplayConflictError("Decision receipt is bound to a different action")
        if current > receipt.expires_at:
            raise ReceiptExpiredError("Decision receipt has expired")

        approval_id = None
        if receipt.decision is Decision.DENY:
            raise ExecutionDeniedError("A denied action cannot execute")
        if receipt.decision is Decision.ESCALATE:
            approval = self._memory.get_human_approval(str(receipt.receipt_id))
            if (
                approval is None
                or approval.action_id != action_id
                or approval.receipt_id != receipt.receipt_id
                or current > approval.expires_at
            ):
                raise ExecutionDeniedError(
                    "An escalated action requires an active action-bound human approval"
                )
            approval_id = approval.approval_id

        key_digest = sha256_text(idempotency_key)
        existing = self._memory.get_execution_authorization(str(receipt_id))
        if existing is not None:
            if not (
                hmac.compare_digest(existing.idempotency_key_digest, key_digest)
                and hmac.compare_digest(existing.request_digest, request_body_digest)
                and existing.action_id == action_id
            ):
                raise ReplayConflictError(
                    "Receipt was already authorized with a different idempotency request"
                )
            return existing, True, []

        authorization = ExecutionAuthorization(
            tenant_id=receipt.tenant_id,
            action_id=action_id,
            receipt_id=receipt_id,
            idempotency_key_digest=key_digest,
            request_digest=request_body_digest,
            human_approval_id=approval_id,
        )
        writes = self._memory.write_execution_authorization(authorization)
        return authorization, False, writes
