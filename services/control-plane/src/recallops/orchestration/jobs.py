"""Deterministic ACP job and payment state transitions."""

from __future__ import annotations

from recallops.models import JobRecord, JobStatus, VerificationOutcome, utc_now


class JobTransitionError(RuntimeError):
    """Raised when a callback attempts an invalid economic state transition."""


class JobStateMachine:
    def mark_submitted(self, job: JobRecord, callback_id: str) -> tuple[JobRecord, bool]:
        return self._transition(job, callback_id, JobStatus.SUBMITTED, {JobStatus.CREATED})

    def verify(
        self,
        job: JobRecord,
        *,
        callback_id: str,
        outcome: VerificationOutcome,
        verifier_id: str,
        reason: str,
    ) -> tuple[JobRecord, bool]:
        if callback_id in job.processed_callback_ids:
            return job, True
        if job.status is not JobStatus.SUBMITTED:
            raise JobTransitionError("Only a submitted job can be verified")
        status = (
            JobStatus.VERIFIED_PASSED
            if outcome is VerificationOutcome.PASSED
            else JobStatus.VERIFIED_FAILED
        )
        return (
            job.model_copy(
                update={
                    "status": status,
                    "verification_outcome": outcome,
                    "verification_reason": reason,
                    "verifier_id": verifier_id,
                    "processed_callback_ids": (*job.processed_callback_ids, callback_id),
                    "updated_at": utc_now(),
                }
            ),
            False,
        )

    def authorize_payment(self, job: JobRecord, callback_id: str) -> tuple[JobRecord, bool]:
        if callback_id in job.processed_callback_ids:
            return job, True
        if job.status is JobStatus.VERIFIED_FAILED:
            raise JobTransitionError("A verified failed job cannot be paid")
        if job.status is not JobStatus.VERIFIED_PASSED:
            raise JobTransitionError("Payment requires a passed verification")
        return self._transition(
            job, callback_id, JobStatus.PAYMENT_AUTHORIZED, {JobStatus.VERIFIED_PASSED}
        )

    @staticmethod
    def _transition(
        job: JobRecord,
        callback_id: str,
        target: JobStatus,
        allowed: set[JobStatus],
    ) -> tuple[JobRecord, bool]:
        if callback_id in job.processed_callback_ids:
            return job, True
        if job.status not in allowed:
            raise JobTransitionError(f"Cannot transition {job.status} to {target}")
        return (
            job.model_copy(
                update={
                    "status": target,
                    "processed_callback_ids": (*job.processed_callback_ids, callback_id),
                    "updated_at": utc_now(),
                }
            ),
            False,
        )
