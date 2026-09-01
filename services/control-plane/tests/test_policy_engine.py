from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from recallops.demo.common import action, budget, policy
from recallops.models import Decision, EvaluationContext, MemoryTier, StoredMemory
from recallops.policy.engine import PolicyEngine


def memory(record_type: str, body: Mapping[str, object]) -> StoredMemory:
    return StoredMemory(
        tier=MemoryTier.WARM,
        record_type=record_type,
        record_name=f"{record_type}:test",
        body=dict(body),
        written_at=datetime.now(UTC),
    )


def test_matching_failure_changes_decision_to_deny() -> None:
    current_session = uuid4()
    proposed = action("agent-a", current_session)
    active_policy = policy()
    account = budget(current_session)
    failure_body = {
        "tenant_id": proposed.tenant_id,
        "provider_id": proposed.provider_id,
        "task_category": proposed.task_category,
        "task_fingerprint": proposed.task_fingerprint,
        "verifier_id": "deterministic-schema-verifier-v1",
        "verification_reason": "Evidence missing.",
        "source_session_id": str(current_session),
        "job_reference": None,
        "failed_at": datetime.now(UTC).isoformat(),
        "active": True,
    }
    context = EvaluationContext(
        policy=memory("owner_policy", active_policy.model_dump(mode="json")),
        budget=memory("budget_account", account.model_dump(mode="json")),
        matching_failure=memory("failure_fingerprint", failure_body),
    )

    receipt = PolicyEngine().evaluate(proposed, context)

    assert receipt.decision is Decision.DENY
    assert "REPEATED_FAILURE_FINGERPRINT" in receipt.reason_codes
    assert any(item.record_type == "failure_fingerprint" for item in receipt.memory_evidence)


def test_cumulative_budget_uses_decimal_arithmetic() -> None:
    current_session = uuid4()
    proposed = action("agent-b", current_session).model_copy(
        update={"requested_amount": Decimal("0.100001")}
    )
    active_policy = policy().model_copy(update={"cumulative_budget": Decimal("5.000000")})
    account = budget(current_session).model_copy(update={"spent": Decimal("4.900000")})
    context = EvaluationContext(
        policy=memory("owner_policy", active_policy.model_dump(mode="json")),
        budget=memory("budget_account", account.model_dump(mode="json")),
        matching_failure=None,
    )

    receipt = PolicyEngine().evaluate(proposed, context)

    assert receipt.decision is Decision.DENY
    assert receipt.budget_after_if_approved == Decimal("5.000001")
    assert receipt.reason_codes == ("CUMULATIVE_BUDGET_EXCEEDED",)


def test_missing_policy_fails_closed() -> None:
    proposed = action("agent-b", uuid4())
    receipt = PolicyEngine().evaluate(
        proposed, EvaluationContext(policy=None, budget=None, matching_failure=None)
    )
    assert receipt.decision is Decision.ESCALATE
    assert receipt.reason_codes == ("MISSING_OWNER_POLICY",)


def test_expired_budget_window_escalates() -> None:
    current_session = uuid4()
    old = datetime.now(UTC) - timedelta(days=2)
    active_policy = policy(old)
    account = budget(current_session, old)
    receipt = PolicyEngine().evaluate(
        action("agent-b", current_session),
        EvaluationContext(
            policy=memory("owner_policy", active_policy.model_dump(mode="json")),
            budget=memory("budget_account", account.model_dump(mode="json")),
            matching_failure=None,
        ),
    )
    assert receipt.decision is Decision.ESCALATE
    assert receipt.reason_codes == ("BUDGET_WINDOW_INACTIVE",)
