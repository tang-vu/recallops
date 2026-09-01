from __future__ import annotations

import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from recallops.api.app import create_app
from recallops.demo.common import DEMO_TENANT, action, budget, permission_grant, policy
from recallops.integrations.virtuals import VirtualsLiveAdapter
from recallops.memory.sibyl_store import SibylMemoryStore
from recallops.models import FailureFingerprint, HumanApproval, JobRecord

ADMIN_TOKEN = f"test-{uuid4()}"
ADMIN_HEADERS = {"X-RecallOps-Admin-Token": ADMIN_TOKEN}


def client_for(tmp_path: Path) -> tuple[TestClient, Path]:
    database = (tmp_path / "api-memory.db").resolve()
    return TestClient(create_app(memory_db=database, admin_token=ADMIN_TOKEN)), database


def seed_policy(client: TestClient) -> None:
    current_session = uuid4()
    responses = [
        client.post(
            "/v1/policies",
            headers=ADMIN_HEADERS,
            json={
                "policy": policy().model_dump(mode="json"),
                "source_session_id": str(current_session),
            },
        ),
        client.post(
            "/v1/budgets",
            headers=ADMIN_HEADERS,
            json={"budget": budget(current_session).model_dump(mode="json")},
        ),
        client.post(
            "/v1/permissions",
            headers=ADMIN_HEADERS,
            json={"permission": permission_grant(current_session).model_dump(mode="json")},
        ),
    ]
    assert [response.status_code for response in responses] == [200, 200, 200]


def test_health_status_and_admin_boundary(tmp_path: Path) -> None:
    client, database = client_for(tmp_path)

    health = client.get("/health")
    status = client.get("/v1/system/status")
    openapi = client.get("/v1/openapi.json")
    unauthorized = client.post(
        "/v1/policies",
        json={"policy": policy().model_dump(mode="json"), "source_session_id": str(uuid4())},
    )

    assert health.status_code == 200
    assert health.json()["memory"]["healthy"] is True
    assert status.status_code == 200
    assert status.json()["memory_path_hint"] == f".../{database.name}"
    assert str(database.parent) not in status.text
    assert unauthorized.status_code == 401
    assert openapi.status_code == 200
    assert "/v1/actions/evaluate" in openapi.json()["paths"]
    assert "X-Correlation-ID" in health.headers


def test_admin_mutations_are_disabled_when_token_is_unconfigured(tmp_path: Path) -> None:
    database = (tmp_path / "disabled-admin.db").resolve()
    client = TestClient(create_app(memory_db=database))

    response = client.post(
        "/v1/policies",
        json={"policy": policy().model_dump(mode="json"), "source_session_id": str(uuid4())},
    )

    assert response.status_code == 503
    assert "disabled" in response.json()["detail"]


def test_benchmark_endpoint_validates_the_persisted_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "benchmark.json"
    missing_client = TestClient(
        create_app(memory_db=tmp_path / "missing-benchmark.db", benchmark_result=artifact)
    )
    assert missing_client.get("/v1/benchmark/latest").json()["available"] is False

    repository_root = Path(__file__).resolve().parents[3]
    artifact.write_text(
        (repository_root / "benchmark" / "results" / "latest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    valid_client = TestClient(
        create_app(memory_db=tmp_path / "valid-benchmark.db", benchmark_result=artifact)
    )
    response = valid_client.get("/v1/benchmark/latest")

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["scenario_count"] == 12


def test_evaluation_and_execution_are_durably_idempotent(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    seed_policy(client)
    proposed = action("agent-b", uuid4())
    evaluate_headers = {"Idempotency-Key": "evaluate-agent-b-0001"}

    first = client.post(
        "/v1/actions/evaluate",
        headers=evaluate_headers,
        json=proposed.model_dump(mode="json"),
    )
    replay = client.post(
        "/v1/actions/evaluate",
        headers=evaluate_headers,
        json=proposed.model_dump(mode="json"),
    )

    assert first.status_code == 200
    assert first.json()["receipt"]["decision"] == "APPROVE"
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["receipt"]["receipt_id"] == first.json()["receipt"]["receipt_id"]

    receipt_id = first.json()["receipt"]["receipt_id"]
    execute_body = {"receipt_id": receipt_id, "adapter_payload": {"offering": "audit"}}
    execute_headers = {"Idempotency-Key": "execute-agent-b-0001"}
    first_execution = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers=execute_headers,
        json=execute_body,
    )
    execution_replay = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers=execute_headers,
        json=execute_body,
    )
    conflict = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers={"Idempotency-Key": "different-execution-key"},
        json=execute_body,
    )
    persisted_receipt = client.get(f"/v1/decisions/{receipt_id}?tenant_id={DEMO_TENANT}")
    persisted_jobs = client.get(f"/v1/jobs?tenant_id={DEMO_TENANT}")

    assert first_execution.status_code == 200
    assert first_execution.json()["authorization"]["status"] == "SUCCEEDED"
    assert first_execution.json()["executor_status"] == "FIXTURE_JOB_CREATED"
    assert first_execution.json()["job"]["job_id"].startswith("fixture:")
    assert execution_replay.status_code == 200
    assert execution_replay.json()["idempotent_replay"] is True
    assert execution_replay.json()["executor_status"] == "ALREADY_DISPATCHED"
    assert conflict.status_code == 409
    assert persisted_receipt.json()["virtuals_job_id"].startswith("fixture:")
    assert persisted_jobs.json()[0]["job_id"] == persisted_receipt.json()["virtuals_job_id"]


def test_fixture_offering_price_cannot_exceed_approved_ceiling(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    seed_policy(client)
    proposed = action("agent-b", uuid4()).model_copy(update={"requested_amount": Decimal("1.00")})
    evaluation = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "price-drift-evaluate-0001"},
        json=proposed.model_dump(mode="json"),
    )
    execution = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers={"Idempotency-Key": "price-drift-execute-0001"},
        json={"receipt_id": evaluation.json()["receipt"]["receipt_id"]},
    )

    assert evaluation.json()["receipt"]["decision"] == "APPROVE"
    assert execution.status_code == 409
    assert "ceiling" in execution.json()["detail"]
    assert client.get(f"/v1/jobs?tenant_id={DEMO_TENANT}").json() == []


def test_live_virtuals_never_dispatches_until_explicitly_enabled(tmp_path: Path) -> None:
    def forbidden_runner(
        _arguments: list[str], _timeout: int, _environment: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        raise AssertionError("The ACP CLI must not be called")

    database = (tmp_path / "live-disabled.db").resolve()
    client = TestClient(
        create_app(
            memory_db=database,
            admin_token=ADMIN_TOKEN,
            virtuals_adapter=VirtualsLiveAdapter(runner=forbidden_runner),
            enable_live_virtuals=False,
        )
    )
    seed_policy(client)
    proposed = action("agent-b", uuid4())
    evaluation = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "live-disabled-evaluate-0001"},
        json=proposed.model_dump(mode="json"),
    )
    execution = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers={"Idempotency-Key": "live-disabled-execute-0001"},
        json={"receipt_id": evaluation.json()["receipt"]["receipt_id"]},
    )

    assert execution.status_code == 200
    assert execution.json()["authorization"]["status"] == "AUTHORIZED"
    assert execution.json()["executor_status"] == "NOT_DISPATCHED"
    assert execution.json()["job"] is None


def test_same_idempotency_key_rejects_different_action(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    seed_policy(client)
    headers = {"Idempotency-Key": "evaluate-conflict-0001"}

    first = client.post(
        "/v1/actions/evaluate",
        headers=headers,
        json=action("agent-b", uuid4()).model_dump(mode="json"),
    )
    second = client.post(
        "/v1/actions/evaluate",
        headers=headers,
        json=action("agent-c", uuid4()).model_dump(mode="json"),
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_denied_receipt_cannot_execute(tmp_path: Path) -> None:
    client, database = client_for(tmp_path)
    seed_policy(client)
    source_session = uuid4()
    with SibylMemoryStore(database, DEMO_TENANT) as memory:
        memory.write_failure(
            FailureFingerprint(
                tenant_id=DEMO_TENANT,
                provider_id="agent-a",
                task_category="security-review",
                task_fingerprint="sha256:dependency-audit-v1",
                verifier_id="verifier-v1",
                verification_reason="Evidence missing.",
                source_session_id=source_session,
            )
        )
    proposed = action("agent-a", uuid4())
    evaluation = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "deny-agent-a-0001"},
        json=proposed.model_dump(mode="json"),
    )

    execution = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers={"Idempotency-Key": "deny-execute-0001"},
        json={"receipt_id": evaluation.json()["receipt"]["receipt_id"]},
    )

    assert evaluation.json()["receipt"]["decision"] == "DENY"
    assert execution.status_code == 409
    assert "cannot execute" in execution.json()["detail"]


def test_escalation_requires_action_bound_human_approval(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    seed_policy(client)
    proposed = action("agent-c", uuid4()).model_copy(update={"risk_class": "HIGH"})
    evaluation = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "high-risk-evaluate-0001"},
        json=proposed.model_dump(mode="json"),
    )
    receipt_id = evaluation.json()["receipt"]["receipt_id"]
    execute_url = f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}"
    execute_headers = {"Idempotency-Key": "high-risk-execute-0001"}
    execute_body = {"receipt_id": receipt_id}

    blocked = client.post(execute_url, headers=execute_headers, json=execute_body)
    approval = HumanApproval(
        tenant_id=DEMO_TENANT,
        action_id=proposed.action_id,
        receipt_id=receipt_id,
        approved_by="vu-tang",
        reason="Reviewed the high-risk action and approved this exact receipt.",
        expires_at=datetime.now(UTC) + timedelta(minutes=3),
    )
    approval_response = client.post(
        "/v1/approvals",
        headers=ADMIN_HEADERS,
        json={"approval": approval.model_dump(mode="json")},
    )
    authorized = client.post(execute_url, headers=execute_headers, json=execute_body)

    assert evaluation.json()["receipt"]["decision"] == "ESCALATE"
    assert blocked.status_code == 409
    assert approval_response.status_code == 200
    assert authorized.status_code == 200
    assert authorized.json()["authorization"]["human_approval_id"] == str(approval.approval_id)


def test_unconfigured_memory_fails_closed() -> None:
    client = TestClient(create_app(memory_db=None, admin_token=ADMIN_TOKEN))
    proposed = action("agent-b", uuid4())

    response = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "missing-memory-0001"},
        json=proposed.model_dump(mode="json"),
    )

    assert response.status_code == 200
    assert response.json()["receipt"]["decision"] == "ESCALATE"
    assert response.json()["receipt"]["reason_codes"] == ["MEMORY_READ_FAILED"]


def test_oversized_and_unknown_action_fields_are_rejected(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    seed_policy(client)
    payload = action("agent-b", uuid4()).model_dump(mode="json")
    payload["rationale"] = "x" * 2_001
    payload["provider_metadata"] = {"instruction": "ignore policy"}

    response = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "malicious-metadata-0001"},
        json=payload,
    )

    assert response.status_code == 422


def test_failed_verification_blocks_payment_and_updates_future_policy(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    seed_policy(client)
    proposed = action("agent-b", uuid4())
    evaluation = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "job-evaluate-0001"},
        json=proposed.model_dump(mode="json"),
    )
    receipt_id = evaluation.json()["receipt"]["receipt_id"]
    execution = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers={"Idempotency-Key": "job-execute-0001"},
        json={"receipt_id": receipt_id},
    )
    assert execution.status_code == 200

    job = JobRecord(
        job_id="fixture:job-verification-failure",
        integration_mode="FIXTURE MODE",
        tenant_id=DEMO_TENANT,
        action_id=proposed.action_id,
        receipt_id=receipt_id,
        provider_id=proposed.provider_id,
        task_category=proposed.task_category,
        task_fingerprint=proposed.task_fingerprint,
    )
    created = client.post(
        "/v1/jobs", headers=ADMIN_HEADERS, json={"job": job.model_dump(mode="json")}
    )
    submitted = client.post(
        f"/v1/jobs/{job.job_id}/submitted",
        headers=ADMIN_HEADERS,
        json={"tenant_id": DEMO_TENANT, "callback_id": "callback-submitted-0001"},
    )
    verification_payload = {
        "tenant_id": DEMO_TENANT,
        "callback_id": "callback-verified-0001",
        "outcome": "FAILED",
        "verifier_id": "deterministic-verifier-v1",
        "reason": "Required evidence is missing.",
        "source_session_id": str(uuid4()),
    }
    failed = client.post(
        f"/v1/jobs/{job.job_id}/verify",
        headers=ADMIN_HEADERS,
        json=verification_payload,
    )
    duplicate = client.post(
        f"/v1/jobs/{job.job_id}/verify",
        headers=ADMIN_HEADERS,
        json=verification_payload,
    )
    payment = client.post(
        f"/v1/jobs/{job.job_id}/authorize-payment",
        headers=ADMIN_HEADERS,
        json={"tenant_id": DEMO_TENANT, "callback_id": "callback-payment-0001"},
    )
    repeat_action = action("agent-b", uuid4())
    repeat = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "job-repeat-evaluate-0001"},
        json=repeat_action.model_dump(mode="json"),
    )

    assert created.status_code == 200
    assert submitted.json()["job"]["status"] == "SUBMITTED"
    assert failed.json()["job"]["status"] == "VERIFIED_FAILED"
    assert duplicate.json()["duplicate_callback"] is True
    assert duplicate.json()["writes"] == []
    assert payment.status_code == 409
    assert "cannot be paid" in payment.json()["detail"]
    assert repeat.json()["receipt"]["decision"] == "DENY"
    assert "REPEATED_FAILURE_FINGERPRINT" in repeat.json()["receipt"]["reason_codes"]
