"""Mandatory memory gate placed before every commerce execution adapter."""

from __future__ import annotations

from recallops.memory.port import MemoryPort, MemorySubsystemError
from recallops.models import DecisionReceipt, ProposedAction
from recallops.policy.engine import PolicyEngine


class CommerceGuard:
    """Load durable context, evaluate deterministically, then persist the receipt."""

    def __init__(self, memory: MemoryPort, engine: PolicyEngine | None = None) -> None:
        self._memory = memory
        self._engine = engine or PolicyEngine()

    def evaluate(self, action: ProposedAction) -> tuple[DecisionReceipt, list[dict[str, str]]]:
        try:
            context = self._memory.load_evaluation_context(
                owner_id=action.owner_id,
                provider_id=action.provider_id,
                task_category=action.task_category,
                task_fingerprint=action.task_fingerprint,
            )
        except MemorySubsystemError:
            return (
                self._engine.fail_closed(
                    action,
                    "MEMORY_READ_FAILED",
                    "Mandatory Sibyl Memory could not be retrieved; commerce is stopped.",
                ),
                [],
            )

        receipt = self._engine.evaluate(action, context)
        try:
            writes = self._memory.write_decision(receipt)
        except MemorySubsystemError:
            return (
                self._engine.fail_closed(
                    action,
                    "MEMORY_WRITE_FAILED",
                    "The decision could not be persisted to Sibyl Memory; commerce is stopped.",
                ),
                [],
            )
        return receipt, writes
