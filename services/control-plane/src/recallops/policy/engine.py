"""Pure deterministic policy evaluation for economic actions."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from recallops.models import (
    BudgetAccount,
    Decision,
    DecisionReceipt,
    EvaluationContext,
    MemoryEvidence,
    OwnerPolicy,
    ProposedAction,
    StoredMemory,
    utc_now,
)


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class PolicyEngine:
    """Evaluate recalled memory without an LLM or nondeterministic heuristics."""

    def evaluate(self, action: ProposedAction, context: EvaluationContext) -> DecisionReceipt:
        if context.policy is None:
            return self.fail_closed(
                action, "MISSING_OWNER_POLICY", "Owner policy memory is missing."
            )
        if context.budget is None:
            return self.fail_closed(action, "MISSING_BUDGET_MEMORY", "Budget memory is missing.")

        try:
            policy = OwnerPolicy.model_validate(
                {
                    key: value
                    for key, value in context.policy.body.items()
                    if key in OwnerPolicy.model_fields
                }
            )
            budget = BudgetAccount.model_validate(context.budget.body)
        except ValidationError:
            return self.fail_closed(
                action,
                "CORRUPT_MANDATORY_MEMORY",
                "Mandatory policy or budget memory failed strict validation.",
            )
        evidence = [
            self._evidence(context.policy, "Defined the active spending and verification limits."),
            self._evidence(context.budget, "Established cumulative spend before this action."),
        ]
        budget_after = budget.spent + action.requested_amount

        if not (
            policy.window_started_at <= action.proposed_at <= policy.window_ends_at
            and budget.window_started_at <= action.proposed_at <= budget.window_ends_at
        ):
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.ESCALATE,
                ("BUDGET_WINDOW_INACTIVE",),
                "The recalled budget window is not active for this action timestamp.",
                evidence,
            )

        if action.currency != policy.currency or action.chain != policy.chain:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("POLICY_CURRENCY_OR_CHAIN_MISMATCH",),
                "The proposed currency or chain is not allowed by the owner policy.",
                evidence,
            )

        if action.requested_amount > policy.per_action_limit:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("PER_ACTION_LIMIT_EXCEEDED",),
                "The requested amount exceeds the per-action limit.",
                evidence,
            )

        if budget_after > policy.cumulative_budget:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("CUMULATIVE_BUDGET_EXCEEDED",),
                "The action would exceed the durable cumulative budget.",
                evidence,
            )

        if policy.require_verifier and action.required_verifier is None:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.ESCALATE,
                ("MISSING_REQUIRED_VERIFIER",),
                "The owner policy requires a verifier before commerce can proceed.",
                evidence,
            )

        if context.matching_failure is not None:
            evidence.append(
                self._evidence(
                    context.matching_failure,
                    "Matched the same provider, task category, and failure fingerprint.",
                )
            )
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("REPEATED_FAILURE_FINGERPRINT", "COUNTERPARTY_ON_PROBATION"),
                "This provider previously failed verification for the same task fingerprint.",
                evidence,
                risk={"level": "HIGH", "matching_failure": True},
            )

        return self._receipt(
            action,
            policy,
            budget.spent,
            budget_after,
            Decision.APPROVE,
            ("POLICY_CHECKS_PASSED",),
            "The action is within budget and no matching adverse memory was recalled.",
            evidence,
            risk={"level": action.risk_class, "matching_failure": False},
        )

    def fail_closed(
        self, action: ProposedAction, reason_code: str, summary: str
    ) -> DecisionReceipt:
        return self._receipt(
            action,
            None,
            Decimal("0"),
            Decimal("0"),
            Decision.ESCALATE,
            (reason_code,),
            summary,
            [],
            risk={"level": "UNKNOWN", "memory_failure": True},
        )

    def _receipt(
        self,
        action: ProposedAction,
        policy: OwnerPolicy | None,
        budget_before: Decimal,
        budget_after: Decimal,
        decision: Decision,
        reason_codes: tuple[str, ...],
        summary: str,
        evidence: list[MemoryEvidence],
        risk: dict[str, Any] | None = None,
    ) -> DecisionReceipt:
        snapshot_digest = _digest([item.model_dump(mode="json") for item in evidence])
        return DecisionReceipt(
            decision=decision,
            action_id=action.action_id,
            tenant_id=action.tenant_id,
            session_id=action.session_id,
            policy_version=policy.version if policy else "unavailable",
            reason_codes=reason_codes,
            human_summary=summary,
            memory_evidence=tuple(evidence),
            budget_before=budget_before,
            budget_after_if_approved=budget_after,
            counterparty_risk=risk or {"level": action.risk_class},
            memory_snapshot_digest=snapshot_digest,
        )

    @staticmethod
    def _evidence(memory: StoredMemory, why: str) -> MemoryEvidence:
        return MemoryEvidence(
            tier=memory.tier,
            record_type=memory.record_type,
            record_name=memory.record_name,
            source_session_id=memory.source_session_id,
            written_at=memory.written_at,
            recalled_at=utc_now(),
            why_it_mattered=why,
            status=memory.status,
            content=memory.body,
            content_digest=_digest(memory.body),
        )
