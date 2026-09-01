from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from recallops.api.app import create_app
from recallops.demo.common import DEMO_TENANT, action, budget, permission_grant, policy
from recallops.integrations.base import (
    BASE_SEPOLIA_CHAIN_ID,
    LOCAL_ANVIL_CHAIN_ID,
    BaseAdapterError,
    BaseAnchorRequest,
    BaseAnchorResult,
    BaseViemAdapter,
)
from recallops.models import Decision

ADMIN_TOKEN = f"test-{uuid4()}"
ADMIN_HEADERS = {"X-RecallOps-Admin-Token": ADMIN_TOKEN}
CONTRACT = "0x1111111111111111111111111111111111111111"
SUBMITTER = "0x2222222222222222222222222222222222222222"
TRANSACTION = "0x" + "33" * 32


def anchor_request() -> BaseAnchorRequest:
    return BaseAnchorRequest(
        tenant_id="tenant-a",
        receipt_id=uuid4(),
        action_id=uuid4(),
        decision=Decision.APPROVE,
        decision_digest="0x" + "44" * 32,
        acp_job_reference="fixture:job",
    )


def result_for(
    request: BaseAnchorRequest, *, chain_id: int = LOCAL_ANVIL_CHAIN_ID
) -> dict[str, object]:
    return {
        "ok": True,
        "chainId": chain_id,
        "contractAddress": CONTRACT,
        "transactionHash": TRANSACTION,
        "receiptIdDigest": "0x" + "55" * 32,
        "decisionDigest": request.decision_digest,
        "acpJobReferenceDigest": "0x" + "66" * 32,
        "recordHash": "0x" + "77" * 32,
        "explorerUrl": None,
        "created": True,
        "verified": True,
    }


def test_viem_adapter_uses_stdin_without_leaking_unapproved_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object], Mapping[str, str]]] = []
    request = anchor_request()
    monkeypatch.setenv("RECALLOPS_UNRELATED_SECRET", "must-not-reach-node")

    def runner(
        arguments: list[str],
        input_text: str,
        _timeout: int,
        environment: Mapping[str, str],
    ) -> subprocess.CompletedProcess[str]:
        calls.append((arguments, json.loads(input_text), environment))
        return subprocess.CompletedProcess(
            arguments, 0, stdout=json.dumps(result_for(request)), stderr=""
        )

    adapter = BaseViemAdapter(
        mode="LOCAL ANVIL",
        chain_id=LOCAL_ANVIL_CHAIN_ID,
        rpc_url="http://127.0.0.1:8547",
        contract_address=CONTRACT,
        submitter=SUBMITTER,
        client_script="dist/cli.js",
        runner=runner,
    )
    result = adapter.anchor(request)

    arguments, payload, environment = calls[0]
    assert arguments == ["node", "dist/cli.js"]
    assert payload["receiptId"] == str(request.receipt_id)
    assert payload["rpcUrl"] == "http://127.0.0.1:8547"
    assert "RECALLOPS_UNRELATED_SECRET" not in environment
    assert result.transaction_hash == TRANSACTION
    assert result.verified is True


def test_live_adapter_requires_two_explicit_gates_and_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        BaseViemAdapter(
            mode="BASE SEPOLIA",
            chain_id=BASE_SEPOLIA_CHAIN_ID,
            rpc_url="http://base.invalid",
            contract_address=CONTRACT,
            submitter=SUBMITTER,
            client_script="dist/cli.js",
        )

    adapter = BaseViemAdapter(
        mode="BASE SEPOLIA",
        chain_id=BASE_SEPOLIA_CHAIN_ID,
        rpc_url="https://base.invalid",
        contract_address=CONTRACT,
        submitter=SUBMITTER,
        client_script="dist/cli.js",
    )
    with pytest.raises(BaseAdapterError, match="explicit wallet approval"):
        adapter.anchor(anchor_request())


class StubBaseAdapter:
    mode = "LOCAL ANVIL"
    chain_id = LOCAL_ANVIL_CHAIN_ID

    def __init__(self) -> None:
        self.calls: list[BaseAnchorRequest] = []

    def anchor(self, request: BaseAnchorRequest) -> BaseAnchorResult:
        self.calls.append(request)
        return BaseAnchorResult(
            chain_id=LOCAL_ANVIL_CHAIN_ID,
            contract_address=CONTRACT,
            transaction_hash=TRANSACTION,
            receipt_id_digest="0x" + "55" * 32,
            decision_digest=request.decision_digest,
            acp_job_reference_digest="0x" + "66" * 32,
            record_hash="0x" + "77" * 32,
            explorer_url=None,
            created=True,
            verified=True,
        )


def _seed_policy(client: TestClient) -> None:
    session_id = uuid4()
    responses = [
        client.post(
            "/v1/policies",
            headers=ADMIN_HEADERS,
            json={
                "policy": policy().model_dump(mode="json"),
                "source_session_id": str(session_id),
            },
        ),
        client.post(
            "/v1/budgets",
            headers=ADMIN_HEADERS,
            json={"budget": budget(session_id).model_dump(mode="json")},
        ),
        client.post(
            "/v1/permissions",
            headers=ADMIN_HEADERS,
            json={"permission": permission_grant(session_id).model_dump(mode="json")},
        ),
    ]
    assert [response.status_code for response in responses] == [200, 200, 200]


def test_api_blocks_anchor_until_job_passes_then_persists_idempotently(tmp_path: Path) -> None:
    adapter = StubBaseAdapter()
    client = TestClient(
        create_app(
            memory_db=(tmp_path / "base-api.db").resolve(),
            admin_token=ADMIN_TOKEN,
            base_adapter=adapter,
        )
    )
    _seed_policy(client)
    proposed = action("agent-b", uuid4())
    evaluated = client.post(
        "/v1/actions/evaluate",
        headers={"Idempotency-Key": "base-evaluate-0001"},
        json=proposed.model_dump(mode="json"),
    ).json()
    receipt_id = evaluated["receipt"]["receipt_id"]
    executed = client.post(
        f"/v1/actions/{proposed.action_id}/execute?tenant_id={DEMO_TENANT}",
        headers={"Idempotency-Key": "base-execute-0001"},
        json={"receipt_id": receipt_id},
    ).json()
    job_id = executed["job"]["job_id"]
    anchor_url = f"/v1/decisions/{receipt_id}/anchor?tenant_id={DEMO_TENANT}"
    anchor_body = {"action_id": str(proposed.action_id)}
    anchor_headers = {**ADMIN_HEADERS, "Idempotency-Key": "base-anchor-0001"}

    blocked = client.post(anchor_url, headers=anchor_headers, json=anchor_body)
    assert blocked.status_code == 409
    assert "pass verification" in blocked.json()["detail"]
    assert adapter.calls == []

    submitted = client.post(
        f"/v1/jobs/{job_id}/submitted",
        headers=ADMIN_HEADERS,
        json={"tenant_id": DEMO_TENANT, "callback_id": "base-submit-callback-0001"},
    )
    verified = client.post(
        f"/v1/jobs/{job_id}/verify",
        headers=ADMIN_HEADERS,
        json={
            "tenant_id": DEMO_TENANT,
            "callback_id": "base-verify-callback-0001",
            "outcome": "PASSED",
            "verifier_id": "deterministic-verifier-v1",
            "reason": "The deterministic fixture satisfied its declared contract.",
            "source_session_id": str(proposed.session_id),
        },
    )
    anchored = client.post(anchor_url, headers=anchor_headers, json=anchor_body)
    replay = client.post(anchor_url, headers=anchor_headers, json=anchor_body)
    receipt = client.get(f"/v1/decisions/{receipt_id}?tenant_id={DEMO_TENANT}")
    recalled_anchor = client.get(f"/v1/decisions/{receipt_id}/anchor?tenant_id={DEMO_TENANT}")

    assert submitted.status_code == 200
    assert verified.status_code == 200
    assert anchored.status_code == 200
    assert anchored.json()["anchor"]["integration_mode"] == "LOCAL ANVIL"
    assert anchored.json()["anchor"]["transaction_hash"] == TRANSACTION
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert len(adapter.calls) == 1
    assert receipt.json()["base_transaction_hash"] == TRANSACTION
    assert recalled_anchor.status_code == 200
    assert recalled_anchor.json()["transaction_hash"] == TRANSACTION
