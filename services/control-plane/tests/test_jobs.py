from uuid import uuid4

import pytest
from pydantic import ValidationError
from recallops.models import JobRecord, VerificationOutcome
from recallops.orchestration.jobs import JobStateMachine, JobTransitionError


def fixture_job() -> JobRecord:
    return JobRecord(
        job_id="fixture:state-machine",
        integration_mode="FIXTURE MODE",
        tenant_id="tenant-a",
        action_id=uuid4(),
        receipt_id=uuid4(),
        provider_id="agent-a",
        task_category="audit",
        task_fingerprint="audit-v1",
    )


def test_duplicate_callback_is_side_effect_free() -> None:
    machine = JobStateMachine()
    submitted, _ = machine.mark_submitted(fixture_job(), "callback-submitted")
    verified, _ = machine.verify(
        submitted,
        callback_id="callback-verified",
        outcome=VerificationOutcome.PASSED,
        verifier_id="verifier-v1",
        reason="All checks passed.",
    )

    duplicate, was_duplicate = machine.verify(
        verified,
        callback_id="callback-verified",
        outcome=VerificationOutcome.PASSED,
        verifier_id="verifier-v1",
        reason="All checks passed.",
    )

    assert was_duplicate is True
    assert duplicate == verified


def test_failed_job_cannot_be_paid() -> None:
    machine = JobStateMachine()
    submitted, _ = machine.mark_submitted(fixture_job(), "callback-submitted")
    failed, _ = machine.verify(
        submitted,
        callback_id="callback-failed",
        outcome=VerificationOutcome.FAILED,
        verifier_id="verifier-v1",
        reason="Evidence missing.",
    )

    with pytest.raises(JobTransitionError, match="cannot be paid"):
        machine.authorize_payment(failed, "callback-payment")


def test_fixture_job_id_must_be_visibly_labeled() -> None:
    with pytest.raises(ValidationError, match="fixture:"):
        JobRecord.model_validate(
            {**fixture_job().model_dump(mode="json"), "job_id": "looks-real-123"}
        )
