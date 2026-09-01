"""Narrow memory protocol used by the production guard and tests."""

from __future__ import annotations

from typing import Protocol

from recallops.models import (
    BudgetAccount,
    DecisionReceipt,
    EvaluationContext,
    FailureFingerprint,
    OwnerPolicy,
)


class MemorySubsystemError(RuntimeError):
    """Raised when mandatory durable memory cannot be read or written."""


class MemoryPort(Protocol):
    """Economic memory needed by the guard.

    SibylMemoryStore is the only production implementation. A stateless
    implementation may exist later only inside the comparison benchmark.
    """

    def set_active_session(self, session_id: str, metadata: dict[str, str]) -> None: ...

    def write_policy(self, policy: OwnerPolicy, source_session_id: str) -> list[dict[str, str]]: ...

    def write_budget(self, account: BudgetAccount) -> list[dict[str, str]]: ...

    def write_failure(self, failure: FailureFingerprint) -> list[dict[str, str]]: ...

    def load_evaluation_context(
        self,
        *,
        owner_id: str,
        provider_id: str,
        task_category: str,
        task_fingerprint: str,
    ) -> EvaluationContext: ...

    def write_decision(self, receipt: DecisionReceipt) -> list[dict[str, str]]: ...

    def close(self) -> None: ...
