from __future__ import annotations

from typing import cast
from uuid import uuid4

from recallops.demo.common import action
from recallops.memory.port import MemoryPort, MemorySubsystemError
from recallops.models import Decision
from recallops.orchestration.guard import CommerceGuard


class _ReadFailure:
    def load_evaluation_context(self, **_kwargs: str) -> None:
        raise MemorySubsystemError("simulated unavailable Sibyl")


def test_memory_read_failure_escalates_and_stops_commerce() -> None:
    guard = CommerceGuard(cast(MemoryPort, _ReadFailure()))

    receipt, writes = guard.evaluate(action("agent-b", uuid4()))

    assert receipt.decision is Decision.ESCALATE
    assert receipt.reason_codes == ("MEMORY_READ_FAILED",)
    assert receipt.counterparty_risk["memory_failure"] is True
    assert writes == []
