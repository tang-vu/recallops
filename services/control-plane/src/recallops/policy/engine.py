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
    HumanException,
    MemoryEvidence,
    OwnerPolicy,
    PermissionGrant,
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
            permission = (
                PermissionGrant.model_validate(context.permission.body)
                if context.permission is not None
                else None
            )
            exception = (
                HumanException.model_validate(context.human_exception.body)
                if context.human_exception is not None
                else None
            )
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
        if context.permission is not None:
            evidence.append(
                self._evidence(
                    context.permission,
                    "Established whether the requesting agent may exercise this permission.",
                )
            )
        if context.human_exception is not None:
            evidence.append(
                self._evidence(
                    context.human_exception,
                    "Established whether a human-approved exception is active and scoped.",
                )
            )
        budget_after = budget.spent + action.requested_amount

        if (
            policy.tenant_id != action.tenant_id
            or policy.owner_id != action.owner_id
            or budget.tenant_id != action.tenant_id
            or budget.owner_id != action.owner_id
            or budget.currency != policy.currency
        ):
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.ESCALATE,
                ("CONFLICTING_POLICY_MEMORY",),
                "Mandatory policy and budget memories conflict with the proposed action.",
                evidence,
            )

        if action.provider_id in policy.prohibited_providers:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("PROHIBITED_PROVIDER",),
                "The owner policy explicitly prohibits this provider.",
                evidence,
            )

        if permission is None:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("MISSING_PERMISSION",),
                "No durable permission grant authorizes this action.",
                evidence,
            )

        if permission.revoked_at is not None:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("PERMISSION_REVOKED",),
                "The permission being exercised was explicitly revoked.",
                evidence,
            )

        if not permission.valid_from <= action.proposed_at <= permission.expires_at:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("PERMISSION_EXPIRED_OR_INACTIVE",),
                "The permission is not active for this action timestamp.",
                evidence,
            )

        if (
            permission.tenant_id != action.tenant_id
            or permission.owner_id != action.owner_id
            or permission.requesting_agent_id != action.requesting_agent_id
            or permission.permission != action.permission
            or permission.provider_id not in (None, action.provider_id)
            or (
                permission.task_categories
                and action.task_category not in permission.task_categories
            )
        ):
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.DENY,
                ("INVALID_PERMISSION_SCOPE",),
                "The recalled permission does not cover this action scope.",
                evidence,
            )

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

        if action.evidence_confidence < policy.minimum_evidence_confidence:
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.ESCALATE,
                ("INSUFFICIENT_EVIDENCE_CONFIDENCE",),
                "The proposed evidence confidence is below the owner's minimum.",
                evidence,
            )

        valid_exception = False
        if exception is not None:
            if exception.revoked_at is not None or not (
                exception.valid_from <= action.proposed_at <= exception.expires_at
            ):
                return self._receipt(
                    action,
                    policy,
                    budget.spent,
                    budget_after,
                    Decision.ESCALATE,
                    ("EXPIRED_OR_REVOKED_HUMAN_EXCEPTION",),
                    "A recalled human exception exists but is no longer valid.",
                    evidence,
                )
            valid_exception = (
                exception.tenant_id == action.tenant_id
                and exception.owner_id == action.owner_id
                and exception.provider_id == action.provider_id
                and exception.task_category == action.task_category
                and exception.task_fingerprint in (None, action.task_fingerprint)
                and exception.currency == action.currency
                and action.requested_amount <= exception.maximum_amount
            )
            if not valid_exception:
                return self._receipt(
                    action,
                    policy,
                    budget.spent,
                    budget_after,
                    Decision.ESCALATE,
                    ("HUMAN_EXCEPTION_SCOPE_MISMATCH",),
                    "The recalled human exception does not cover this exact action.",
                    evidence,
                )

        if context.matching_failure is not None and not valid_exception:
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

        if (
            context.counterparty_profile is not None
            and context.counterparty_profile.status == "probation"
            and not valid_exception
        ):
            evidence.append(
                self._evidence(
                    context.counterparty_profile,
                    "Showed an active task-specific counterparty probation period.",
                )
            )
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.ESCALATE,
                ("COUNTERPARTY_ON_PROBATION",),
                "The counterparty is on probation for this task category.",
                evidence,
                risk={"level": "HIGH", "probation": True},
            )

        if (
            action.risk_class in {"HIGH", "CRITICAL"}
            and policy.high_risk_requires_human
            and not valid_exception
        ):
            return self._receipt(
                action,
                policy,
                budget.spent,
                budget_after,
                Decision.ESCALATE,
                ("HUMAN_APPROVAL_REQUIRED",),
                "High-risk commerce requires a scoped human exception.",
                evidence,
                risk={"level": action.risk_class, "human_review": True},
            )

        return self._receipt(
            action,
            policy,
            budget.spent,
            budget_after,
            Decision.APPROVE,
            (
                ("VALID_HUMAN_EXCEPTION", "POLICY_CHECKS_PASSED")
                if valid_exception
                else ("POLICY_CHECKS_PASSED",)
            ),
            (
                "A valid human exception covers the recalled risk and all hard limits pass."
                if valid_exception
                else "The action is within budget and no matching adverse memory was recalled."
            ),
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
