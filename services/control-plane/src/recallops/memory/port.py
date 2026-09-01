"""Narrow memory protocol used by the production guard and tests."""

from __future__ import annotations

from typing import Protocol

from recallops.models import (
    BaseAnchorRecord,
    BudgetAccount,
    CounterpartyProfile,
    DecisionReceipt,
    EvaluationContext,
    ExecutionAuthorization,
    FailureFingerprint,
    HumanApproval,
    HumanException,
    IdempotencyRecord,
    OwnerPolicy,
    PermissionGrant,
    ProposedAction,
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

    def write_counterparty_profile(self, profile: CounterpartyProfile) -> list[dict[str, str]]: ...

    def write_permission(self, grant: PermissionGrant) -> list[dict[str, str]]: ...

    def write_exception(self, exception: HumanException) -> list[dict[str, str]]: ...

    def load_evaluation_context(
        self,
        *,
        owner_id: str,
        requesting_agent_id: str,
        provider_id: str,
        task_category: str,
        task_fingerprint: str,
        permission: str,
    ) -> EvaluationContext: ...

    def write_decision(self, receipt: DecisionReceipt) -> list[dict[str, str]]: ...

    def write_proposed_action(self, action: ProposedAction) -> list[dict[str, str]]: ...

    def get_proposed_action(self, action_id: str) -> ProposedAction | None: ...

    def get_decision(self, receipt_id: str) -> DecisionReceipt | None: ...

    def list_decisions(self, limit: int = 100) -> list[DecisionReceipt]: ...

    def write_human_approval(self, approval: HumanApproval) -> list[dict[str, str]]: ...

    def get_human_approval(self, receipt_id: str) -> HumanApproval | None: ...

    def write_execution_authorization(
        self,
        authorization: ExecutionAuthorization,
        event_type: str = "EXECUTION_AUTHORIZED",
    ) -> list[dict[str, str]]: ...

    def get_execution_authorization(self, receipt_id: str) -> ExecutionAuthorization | None: ...

    def write_base_anchor(self, anchor: BaseAnchorRecord) -> list[dict[str, str]]: ...

    def get_base_anchor(self, receipt_id: str) -> BaseAnchorRecord | None: ...

    def write_idempotency_record(self, record: IdempotencyRecord) -> list[dict[str, str]]: ...

    def get_idempotency_record(
        self, operation: str, key_digest: str
    ) -> IdempotencyRecord | None: ...

    def close(self) -> None: ...
