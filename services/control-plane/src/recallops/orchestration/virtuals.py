"""Approval-bound Virtuals dispatch orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from recallops.integrations.virtuals import (
    BASE_SEPOLIA_CHAIN_ID,
    VirtualsAdapterError,
    VirtualsJobRequest,
    VirtualsJobSnapshot,
    VirtualsPort,
)
from recallops.models import (
    ExecutionAuthorization,
    ExecutionStatus,
    JobRecord,
    ProposedAction,
    utc_now,
)


class VirtualsDispatchError(RuntimeError):
    """Base class for safe policy-approved dispatch failures."""


class VirtualsDispatchBlockedError(VirtualsDispatchError):
    """Current metadata or durable state does not permit dispatch."""


class VirtualsDispatchUnavailableError(VirtualsDispatchError):
    """Read-only ACP metadata could not be retrieved."""


class VirtualsDispatchUncertainError(VirtualsDispatchError):
    """A remote write may have happened, so automatic retry is forbidden."""


class VirtualsDispatchMemory(Protocol):
    def get_job(self, job_id: str) -> JobRecord | None: ...

    def write_job(self, job: JobRecord, event_type: str) -> list[dict[str, str]]: ...

    def attach_virtuals_job(self, receipt_id: str, job_id: str) -> list[dict[str, str]]: ...

    def write_execution_authorization(
        self, authorization: ExecutionAuthorization, event_type: str = "EXECUTION_AUTHORIZED"
    ) -> list[dict[str, str]]: ...


@dataclass(frozen=True)
class VirtualsDispatchResult:
    authorization: ExecutionAuthorization
    writes: tuple[dict[str, str], ...]
    executor_status: str
    note: str
    job: JobRecord | None = None
    snapshot: VirtualsJobSnapshot | None = None
    already_dispatched: bool = False


class VirtualsDispatcher:
    """Turn one durable authorization into at most one ACP job."""

    def __init__(self, adapter: VirtualsPort, *, live_enabled: bool) -> None:
        self._adapter = adapter
        self._live_enabled = live_enabled

    def dispatch(
        self,
        *,
        memory: VirtualsDispatchMemory,
        authorization: ExecutionAuthorization,
        action: ProposedAction,
        requirements: dict[str, Any],
    ) -> VirtualsDispatchResult:
        if authorization.status is ExecutionStatus.FAILED:
            raise VirtualsDispatchUncertainError(
                "A prior Virtuals dispatch failed or is uncertain; a new decision is required."
            )
        if authorization.virtuals_job_id is not None:
            existing_job = memory.get_job(authorization.virtuals_job_id)
            if existing_job is None:
                raise VirtualsDispatchBlockedError(
                    "The durable execution references a missing job; commerce is stopped."
                )
            return VirtualsDispatchResult(
                authorization=authorization,
                writes=(),
                executor_status="ALREADY_DISPATCHED",
                note="The same durable Virtuals job is returned without another adapter call.",
                job=existing_job,
                already_dispatched=True,
            )
        if self._adapter.mode == "LIVE VIRTUALS" and not self._live_enabled:
            return VirtualsDispatchResult(
                authorization=authorization,
                writes=(),
                executor_status="NOT_DISPATCHED",
                note=(
                    "LIVE VIRTUALS is configured but dispatch remains disabled until explicit "
                    "wallet, signer, and funding approval is recorded."
                ),
            )

        try:
            request = VirtualsJobRequest(
                tenant_id=action.tenant_id,
                action_id=action.action_id,
                receipt_id=authorization.receipt_id,
                provider_id=action.provider_id,
                offering_name=action.offering,
                requirements=requirements,
                chain_id=BASE_SEPOLIA_CHAIN_ID if action.chain == "base-sepolia" else -1,
                maximum_amount=action.requested_amount,
                currency=action.currency,
            )
        except ValidationError as exc:
            raise VirtualsDispatchBlockedError(
                "The approved action is not valid for ACP dispatch"
            ) from exc

        try:
            offering = self._adapter.get_offering(
                request.provider_id,
                request.offering_name,
                chain_id=request.chain_id,
            )
        except VirtualsAdapterError as exc:
            raise VirtualsDispatchUnavailableError(str(exc)) from exc
        if (
            offering.price is None
            or offering.currency is None
            or offering.currency.upper() != request.currency
            or offering.price > request.maximum_amount
        ):
            raise VirtualsDispatchBlockedError(
                "Current offering metadata does not match the approved currency and ceiling."
            )

        writes: list[dict[str, str]] = []
        executing = authorization.model_copy(
            update={"status": ExecutionStatus.EXECUTING, "updated_at": utc_now()}
        )
        writes.extend(memory.write_execution_authorization(executing, "VIRTUALS_DISPATCH_STARTED"))
        try:
            snapshot = self._adapter.create_job(request)
        except VirtualsAdapterError as exc:
            failed = executing.model_copy(
                update={"status": ExecutionStatus.FAILED, "updated_at": utc_now()}
            )
            memory.write_execution_authorization(failed, "VIRTUALS_DISPATCH_FAILED")
            raise VirtualsDispatchUncertainError(str(exc)) from exc

        job = JobRecord(
            job_id=snapshot.job_id,
            integration_mode=snapshot.integration_mode,
            tenant_id=action.tenant_id,
            action_id=action.action_id,
            receipt_id=authorization.receipt_id,
            provider_id=action.provider_id,
            task_category=action.task_category,
            task_fingerprint=action.task_fingerprint,
            chain_id=snapshot.chain_id,
            offering_name=action.offering,
            deliverable=snapshot.deliverable,
            payment_metadata=snapshot.payment_metadata,
            verifiable_links=snapshot.links,
            adapter_response_digest=snapshot.response_digest,
        )
        writes.extend(memory.write_job(job, "ACP_JOB_OPENED"))
        writes.extend(memory.attach_virtuals_job(str(authorization.receipt_id), snapshot.job_id))
        succeeded = executing.model_copy(
            update={
                "status": ExecutionStatus.SUCCEEDED,
                "virtuals_job_id": snapshot.job_id,
                "updated_at": utc_now(),
            }
        )
        writes.extend(memory.write_execution_authorization(succeeded, "VIRTUALS_JOB_CREATED"))
        return VirtualsDispatchResult(
            authorization=succeeded,
            writes=tuple(writes),
            executor_status=(
                "FIXTURE_JOB_CREATED"
                if self._adapter.mode == "FIXTURE MODE"
                else "LIVE_JOB_CREATED"
            ),
            note=(
                "FIXTURE MODE created an explicitly labeled local ACP lifecycle record."
                if self._adapter.mode == "FIXTURE MODE"
                else "LIVE VIRTUALS created an ACP job after durable policy authorization."
            ),
            job=job,
            snapshot=snapshot,
        )
