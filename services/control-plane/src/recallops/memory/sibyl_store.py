"""Production Sibyl Memory implementation.

Judges can find every shipped runtime Sibyl read and write in this file.
There is intentionally no alternate production persistence implementation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sibyl_memory_client import MemoryClient

from recallops.memory.port import MemorySubsystemError
from recallops.models import (
    BudgetAccount,
    DecisionReceipt,
    EvaluationContext,
    ExecutionAuthorization,
    FailureFingerprint,
    HumanApproval,
    HumanException,
    IdempotencyRecord,
    JobRecord,
    MemoryTier,
    OwnerPolicy,
    PermissionGrant,
    StoredMemory,
    utc_now,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_name(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:24]
    return f"{prefix}:{digest}"


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SibylMemoryStore:
    """Local, durable, tenant-isolated Sibyl Memory store."""

    def __init__(self, database_path: Path, tenant_id: str) -> None:
        if not database_path.is_absolute():
            raise ValueError("RECALLOPS_MEMORY_DB must resolve to an absolute path")
        if database_path.exists() and not database_path.is_file():
            raise ValueError("RECALLOPS_MEMORY_DB must point to a file")
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = database_path
        self._tenant_id = tenant_id
        try:
            self._client = MemoryClient.local(str(database_path), tenant_id=tenant_id)
        except Exception as exc:
            raise MemorySubsystemError("Sibyl Memory could not be opened") from exc

    @property
    def database_path(self) -> Path:
        return self._database_path

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def __enter__(self) -> SibylMemoryStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close all SQLite connections owned by Sibyl, including thread-local handles."""
        self._client.storage.close()

    def health(self) -> dict[str, str | int | bool]:
        try:
            return {
                "healthy": True,
                "tenant_id": self._client.get_tenant(),
                "schema_version": self._client.schema_version(),
                "database_exists": self._database_path.exists(),
            }
        except Exception as exc:
            raise MemorySubsystemError("Sibyl Memory health check failed") from exc

    def set_active_session(self, session_id: str, metadata: dict[str, str]) -> None:
        body = {"session_id": session_id, **metadata, "updated_at": utc_now().isoformat()}
        try:
            # HOT write: mutable workflow state for the currently active process.
            self._client.set_state("recallops:active-session", body)
        except Exception as exc:
            raise MemorySubsystemError("Failed to write active session to Sibyl HOT state") from exc

    def write_policy(self, policy: OwnerPolicy, source_session_id: str) -> list[dict[str, str]]:
        entity_name = _stable_name("owner-policy", policy.owner_id)
        reference_name = f"recallops:policy-schema:{policy.version}"
        body = policy.model_dump(mode="json") | {"source_session_id": source_session_id}
        try:
            # WARM write: stable owner policy keyed deterministically per tenant and owner.
            entity = self._client.set_entity("owner_policy", entity_name, body, status="active")
            # REFERENCE write: named policy definition required to interpret the entity.
            self._client.set_reference(
                reference_name,
                {
                    "policy_version": policy.version,
                    "money_encoding": "decimal-string",
                    "decision_set": ["APPROVE", "DENY", "ESCALATE"],
                },
                metadata={"document_type": "recallops-policy-schema"},
            )
            # COLD write: chronological audit event for the policy change.
            event_id = self._client.write_event(
                acted=[f"Owner policy {policy.version} stored for {policy.owner_id}"],
                extra={"event_type": "POLICY_STORED", "entity_name": entity_name},
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write owner policy to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "owner_policy", entity_name, entity["id"]),
            self._write_result(
                MemoryTier.REFERENCE, "policy_schema", reference_name, reference_name
            ),
            self._write_result(MemoryTier.COLD, "POLICY_STORED", event_id, event_id),
        ]

    def write_budget(self, account: BudgetAccount) -> list[dict[str, str]]:
        entity_name = _stable_name("budget-account", account.owner_id, account.currency)
        body = account.model_dump(mode="json")
        try:
            # WARM write: cumulative spending survives process and session boundaries.
            entity = self._client.set_entity("budget_account", entity_name, body, status="active")
            event_id = self._client.write_event(
                acted=[f"Budget account updated for {account.owner_id}"],
                extra={
                    "event_type": "BUDGET_UPDATED",
                    "entity_name": entity_name,
                    "spent": str(account.spent),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write budget account to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "budget_account", entity_name, entity["id"]),
            self._write_result(MemoryTier.COLD, "BUDGET_UPDATED", event_id, event_id),
        ]

    def write_failure(self, failure: FailureFingerprint) -> list[dict[str, str]]:
        failure_name = _stable_name(
            "failure",
            failure.provider_id,
            failure.task_category,
            failure.task_fingerprint,
        )
        profile_name = _stable_name("counterparty", failure.provider_id, failure.task_category)
        body = failure.model_dump(mode="json")
        try:
            # WARM writes: exact failure and task-scoped counterparty consequence.
            failure_entity = self._client.set_entity(
                "failure_fingerprint", failure_name, body, status="active"
            )
            profile_entity = self._client.set_entity(
                "counterparty_profile",
                profile_name,
                {
                    "provider_id": failure.provider_id,
                    "task_category": failure.task_category,
                    "failed_jobs": 1,
                    "successful_jobs": 0,
                    "last_failure_fingerprint": failure.task_fingerprint,
                    "last_verification_reason": failure.verification_reason,
                    "source_session_id": str(failure.source_session_id),
                    "probation_status": "active",
                },
                status="probation",
            )
            # COLD write: verifier rejection is retained chronologically.
            event_id = self._client.write_event(
                evaluated=[
                    f"Verifier {failure.verifier_id} rejected {failure.provider_id}: "
                    f"{failure.verification_reason}"
                ],
                acted=[f"Failure fingerprint {failure.task_fingerprint} activated"],
                extra={
                    "event_type": "VERIFICATION_FAILED",
                    "failure_entity": failure_name,
                    "provider_profile": profile_name,
                    "source_session_id": str(failure.source_session_id),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write verification failure to Sibyl") from exc
        return [
            self._write_result(
                MemoryTier.WARM,
                "failure_fingerprint",
                failure_name,
                failure_entity["id"],
            ),
            self._write_result(
                MemoryTier.WARM,
                "counterparty_profile",
                profile_name,
                profile_entity["id"],
            ),
            self._write_result(MemoryTier.COLD, "VERIFICATION_FAILED", event_id, event_id),
        ]

    def write_permission(self, grant: PermissionGrant) -> list[dict[str, str]]:
        entity_name = _stable_name(
            "permission",
            grant.owner_id,
            grant.requesting_agent_id,
            grant.permission,
            grant.provider_id or "*",
        )
        status = "revoked" if grant.revoked_at is not None else "active"
        event_type = "PERMISSION_REVOKED" if grant.revoked_at is not None else "PERMISSION_GRANTED"
        try:
            entity = self._client.set_entity(
                "permission_grant", entity_name, grant.model_dump(mode="json"), status=status
            )
            event_id = self._client.write_event(
                acted=[f"{event_type}: {grant.permission} for {grant.requesting_agent_id}"],
                extra={
                    "event_type": event_type,
                    "entity_name": entity_name,
                    "source_session_id": str(grant.source_session_id),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write permission grant to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "permission_grant", entity_name, entity["id"]),
            self._write_result(MemoryTier.COLD, event_type, event_id, event_id),
        ]

    def write_exception(self, exception: HumanException) -> list[dict[str, str]]:
        entity_name = _stable_name(
            "human-exception",
            exception.owner_id,
            exception.provider_id,
            exception.task_category,
            exception.task_fingerprint or "*",
        )
        status = "revoked" if exception.revoked_at is not None else "active"
        try:
            entity = self._client.set_entity(
                "human_exception", entity_name, exception.model_dump(mode="json"), status=status
            )
            event_id = self._client.write_event(
                acted=[f"Human exception recorded for {exception.provider_id}"],
                extra={
                    "event_type": "HUMAN_EXCEPTION_RECORDED",
                    "entity_name": entity_name,
                    "exception_id": str(exception.exception_id),
                    "source_session_id": str(exception.source_session_id),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write human exception to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "human_exception", entity_name, entity["id"]),
            self._write_result(MemoryTier.COLD, "HUMAN_EXCEPTION_RECORDED", event_id, event_id),
        ]

    def load_evaluation_context(
        self,
        *,
        owner_id: str,
        requesting_agent_id: str,
        provider_id: str,
        task_category: str,
        task_fingerprint: str,
        permission: str,
    ) -> EvaluationContext:
        """Read all mandatory durable state before a commerce decision."""
        policy_name = _stable_name("owner-policy", owner_id)
        budget_name = _stable_name("budget-account", owner_id, "USDC")
        failure_name = _stable_name("failure", provider_id, task_category, task_fingerprint)
        profile_name = _stable_name("counterparty", provider_id, task_category)
        permission_name = _stable_name(
            "permission", owner_id, requesting_agent_id, permission, provider_id
        )
        wildcard_permission_name = _stable_name(
            "permission", owner_id, requesting_agent_id, permission, "*"
        )
        exception_name = _stable_name(
            "human-exception", owner_id, provider_id, task_category, task_fingerprint
        )
        wildcard_exception_name = _stable_name(
            "human-exception", owner_id, provider_id, task_category, "*"
        )
        try:
            # WARM reads: the shipped runtime's load-bearing policy critical path.
            policy = self._read_optional_entity("owner_policy", policy_name)
            budget = self._read_optional_entity("budget_account", budget_name)
            failure = self._read_optional_entity("failure_fingerprint", failure_name)
            profile = self._read_optional_entity("counterparty_profile", profile_name)
            permission_record = self._read_optional_entity("permission_grant", permission_name)
            if permission_record is None:
                permission_record = self._read_optional_entity(
                    "permission_grant", wildcard_permission_name
                )
            exception = self._read_optional_entity("human_exception", exception_name)
            if exception is None:
                exception = self._read_optional_entity("human_exception", wildcard_exception_name)
        except Exception as exc:
            if isinstance(exc, MemorySubsystemError):
                raise
            raise MemorySubsystemError(
                "Failed to retrieve mandatory policy context from Sibyl"
            ) from exc
        return EvaluationContext(
            policy=policy,
            budget=budget,
            permission=permission_record,
            matching_failure=failure,
            counterparty_profile=profile,
            human_exception=exception,
        )

    def write_decision(self, receipt: DecisionReceipt) -> list[dict[str, str]]:
        entity_name = f"decision:{receipt.receipt_id}"
        body = receipt.model_dump(mode="json")
        try:
            # WARM write: prior decisions are action-bound and inspectable across sessions.
            entity = self._client.set_entity("decision_receipt", entity_name, body, status="active")
            # COLD write: chronological decision audit event.
            event_id = self._client.write_event(
                evaluated=[f"Decision {receipt.decision} for action {receipt.action_id}"],
                extra={
                    "event_type": "DECISION_ISSUED",
                    "receipt_id": str(receipt.receipt_id),
                    "action_id": str(receipt.action_id),
                    "reason_codes": list(receipt.reason_codes),
                    "source_session_id": str(receipt.session_id),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write decision receipt to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "decision_receipt", entity_name, entity["id"]),
            self._write_result(MemoryTier.COLD, "DECISION_ISSUED", event_id, event_id),
        ]

    def get_decision(self, receipt_id: str) -> DecisionReceipt | None:
        memory = self._read_optional_entity("decision_receipt", f"decision:{receipt_id}")
        if memory is None:
            return None
        try:
            return DecisionReceipt.model_validate(memory.body)
        except Exception as exc:
            raise MemorySubsystemError("Stored decision receipt is corrupt") from exc

    def list_decisions(self, limit: int = 100) -> list[DecisionReceipt]:
        try:
            rows = self._client.list_entities("decision_receipt", limit=min(limit, 500))
            return [DecisionReceipt.model_validate(row["body"]) for row in rows]
        except Exception as exc:
            raise MemorySubsystemError("Failed to list decision receipts from Sibyl") from exc

    def get_current_policy(self, owner_id: str) -> OwnerPolicy | None:
        memory = self._read_optional_entity("owner_policy", _stable_name("owner-policy", owner_id))
        if memory is None:
            return None
        try:
            return OwnerPolicy.model_validate(
                {
                    key: value
                    for key, value in memory.body.items()
                    if key in OwnerPolicy.model_fields
                }
            )
        except Exception as exc:
            raise MemorySubsystemError("Stored owner policy is corrupt") from exc

    def list_journal(self, limit: int = 100) -> list[dict[str, Any]]:
        try:
            return cast(list[dict[str, Any]], self._client.read_events(limit=min(limit, 500)))
        except Exception as exc:
            raise MemorySubsystemError("Failed to read Sibyl journal") from exc

    def list_counterparties(self, limit: int = 100) -> list[dict[str, Any]]:
        try:
            return cast(
                list[dict[str, Any]],
                self._client.list_entities("counterparty_profile", limit=min(limit, 500)),
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to list counterparties from Sibyl") from exc

    def write_human_approval(self, approval: HumanApproval) -> list[dict[str, str]]:
        entity_name = f"human-approval:{approval.receipt_id}"
        try:
            entity = self._client.set_entity(
                "human_approval", entity_name, approval.model_dump(mode="json"), status="active"
            )
            event_id = self._client.write_event(
                acted=[f"Human approved receipt {approval.receipt_id}"],
                extra={
                    "event_type": "HUMAN_APPROVAL_RECORDED",
                    "receipt_id": str(approval.receipt_id),
                    "action_id": str(approval.action_id),
                    "approval_id": str(approval.approval_id),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write human approval to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "human_approval", entity_name, entity["id"]),
            self._write_result(MemoryTier.COLD, "HUMAN_APPROVAL_RECORDED", event_id, event_id),
        ]

    def get_human_approval(self, receipt_id: str) -> HumanApproval | None:
        memory = self._read_optional_entity("human_approval", f"human-approval:{receipt_id}")
        if memory is None:
            return None
        try:
            return HumanApproval.model_validate(memory.body)
        except Exception as exc:
            raise MemorySubsystemError("Stored human approval is corrupt") from exc

    def write_execution_authorization(
        self, authorization: ExecutionAuthorization
    ) -> list[dict[str, str]]:
        entity_name = f"execution:{authorization.receipt_id}"
        try:
            entity = self._client.set_entity(
                "execution_authorization",
                entity_name,
                authorization.model_dump(mode="json"),
                status=authorization.status.value.lower(),
            )
            event_id = self._client.write_event(
                acted=[f"Execution authorized for receipt {authorization.receipt_id}"],
                extra={
                    "event_type": "EXECUTION_AUTHORIZED",
                    "receipt_id": str(authorization.receipt_id),
                    "action_id": str(authorization.action_id),
                    "authorization_id": str(authorization.authorization_id),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to authorize execution in Sibyl") from exc
        return [
            self._write_result(
                MemoryTier.WARM, "execution_authorization", entity_name, entity["id"]
            ),
            self._write_result(MemoryTier.COLD, "EXECUTION_AUTHORIZED", event_id, event_id),
        ]

    def get_execution_authorization(self, receipt_id: str) -> ExecutionAuthorization | None:
        memory = self._read_optional_entity("execution_authorization", f"execution:{receipt_id}")
        if memory is None:
            return None
        try:
            return ExecutionAuthorization.model_validate(memory.body)
        except Exception as exc:
            raise MemorySubsystemError("Stored execution authorization is corrupt") from exc

    def write_idempotency_record(self, record: IdempotencyRecord) -> list[dict[str, str]]:
        entity_name = _stable_name("idempotency", record.operation, record.key_digest)
        try:
            entity = self._client.set_entity(
                "idempotency_record",
                entity_name,
                record.model_dump(mode="json"),
                status="active",
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write idempotency record to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "idempotency_record", entity_name, entity["id"])
        ]

    def get_idempotency_record(self, operation: str, key_digest: str) -> IdempotencyRecord | None:
        entity_name = _stable_name("idempotency", operation, key_digest)
        memory = self._read_optional_entity("idempotency_record", entity_name)
        if memory is None:
            return None
        try:
            return IdempotencyRecord.model_validate(memory.body)
        except Exception as exc:
            raise MemorySubsystemError("Stored idempotency record is corrupt") from exc

    def write_job(self, job: JobRecord, event_type: str) -> list[dict[str, str]]:
        entity_name = _stable_name("job", job.job_id)
        try:
            entity = self._client.set_entity(
                "commerce_job",
                entity_name,
                job.model_dump(mode="json"),
                status=job.status.value.lower(),
            )
            event_id = self._client.write_event(
                acted=[f"Job {job.job_id} transitioned to {job.status}"],
                extra={
                    "event_type": event_type,
                    "job_entity": entity_name,
                    "job_id": job.job_id,
                    "action_id": str(job.action_id),
                    "receipt_id": str(job.receipt_id),
                },
            )
        except Exception as exc:
            raise MemorySubsystemError("Failed to write commerce job to Sibyl") from exc
        return [
            self._write_result(MemoryTier.WARM, "commerce_job", entity_name, entity["id"]),
            self._write_result(MemoryTier.COLD, event_type, event_id, event_id),
        ]

    def get_job(self, job_id: str) -> JobRecord | None:
        memory = self._read_optional_entity("commerce_job", _stable_name("job", job_id))
        if memory is None:
            return None
        try:
            return JobRecord.model_validate(memory.body)
        except Exception as exc:
            raise MemorySubsystemError("Stored commerce job is corrupt") from exc

    def _read_optional_entity(self, category: str, name: str) -> StoredMemory | None:
        try:
            raw = self._client.get_entity(category, name)
        except Exception as exc:
            if exc.__class__.__name__ == "NotFoundError":
                return None
            raise MemorySubsystemError(f"Sibyl entity read failed for {category}/{name}") from exc
        body = raw["body"]
        source_session_id = body.get("source_session_id")
        return StoredMemory(
            tier=MemoryTier.WARM,
            record_type=category,
            record_name=name,
            body=body,
            written_at=_parse_timestamp(raw["updated_at"]),
            source_session_id=source_session_id,
            status=raw.get("status") or "active",
        )

    @staticmethod
    def _write_result(
        tier: MemoryTier, record_type: str, record_name: str, sibyl_record_id: str
    ) -> dict[str, str]:
        return {
            "tier": tier.value,
            "record_type": record_type,
            "record_name": record_name,
            "sibyl_record_id": sibyl_record_id,
            "status": "written",
        }
