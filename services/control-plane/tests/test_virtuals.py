from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from recallops.integrations.virtuals import (
    BASE_SEPOLIA_CHAIN_ID,
    VirtualsAdapterError,
    VirtualsFixtureAdapter,
    VirtualsJobRequest,
    VirtualsLiveAdapter,
    sanitize_cli_payload,
)

PROVIDER_ADDRESS = "0x1111111111111111111111111111111111111111"


def request(provider_id: str = "agent-b") -> VirtualsJobRequest:
    return VirtualsJobRequest(
        tenant_id="tenant-a",
        action_id=uuid4(),
        receipt_id=uuid4(),
        provider_id=provider_id,
        offering_name="Deterministic dependency audit",
        requirements={"repository": "public/example"},
        chain_id=BASE_SEPOLIA_CHAIN_ID,
        maximum_amount=Decimal("1.50"),
        currency="USDC",
    )


def test_fixture_mode_is_explicit_and_never_returns_real_looking_proof() -> None:
    adapter = VirtualsFixtureAdapter()

    providers = adapter.discover_providers("Agent B", chain_id=BASE_SEPOLIA_CHAIN_ID, top_k=5)
    snapshot = adapter.create_job(request())
    recalled = adapter.get_job(snapshot.job_id, chain_id=BASE_SEPOLIA_CHAIN_ID)

    assert providers[0].provider_id == "agent-b"
    assert snapshot.integration_mode == "FIXTURE MODE"
    assert snapshot.job_id.startswith("fixture:")
    assert snapshot.links == ()
    assert snapshot.payment_metadata == {"escrow": "not-created", "funded": False}
    assert recalled == snapshot


def test_live_adapter_uses_json_cli_without_a_shell_and_sanitizes_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], int, Mapping[str, str]]] = []
    monkeypatch.setenv("RECALLOPS_TEST_SECRET", "must-not-reach-child")

    def runner(
        arguments: list[str], timeout_seconds: int, environment: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        calls.append((arguments, timeout_seconds, environment))
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=(
                '{"jobId":"42","status":"open",'
                '"jobUrl":"https://app.virtuals.io/jobs/42?access_token=secret"}'
            ),
            stderr="",
        )

    adapter = VirtualsLiveAdapter(executable="acp-test", runner=runner)
    snapshot = adapter.create_job(request(PROVIDER_ADDRESS))

    arguments, timeout_seconds, environment = calls[0]
    assert arguments[:3] == ["acp-test", "client", "create-job"]
    assert arguments[-1] == "--json"
    assert "--provider" in arguments
    assert timeout_seconds == 30
    assert environment["IS_TESTNET"] == "true"
    assert "RECALLOPS_TEST_SECRET" not in environment
    assert snapshot.job_id == "42"
    assert snapshot.integration_mode == "LIVE VIRTUALS"
    assert snapshot.links == ("https://app.virtuals.io/jobs/42",)


def test_live_discovery_captures_offering_metadata() -> None:
    def runner(
        arguments: list[str], _timeout_seconds: int, _environment: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        payload: dict[str, Any] = {
            "data": [
                {
                    "walletAddress": PROVIDER_ADDRESS,
                    "name": "Audit Agent",
                    "chains": [{"id": 1, "chainId": BASE_SEPOLIA_CHAIN_ID}],
                    "offerings": [
                        {
                            "name": "Dependency Audit",
                            "description": "Checks dependencies",
                            "priceValue": "1.25",
                            "requirements": {"type": "object"},
                        }
                    ],
                }
            ]
        }
        return subprocess.CompletedProcess(arguments, 0, stdout=json_text(payload), stderr="")

    adapter = VirtualsLiveAdapter(runner=runner)
    providers = adapter.discover_providers("audit", chain_id=BASE_SEPOLIA_CHAIN_ID, top_k=5)
    offering = adapter.get_offering(
        PROVIDER_ADDRESS, "Dependency Audit", chain_id=BASE_SEPOLIA_CHAIN_ID
    )

    assert providers[0].wallet_address == PROVIDER_ADDRESS
    assert providers[0].chain_ids == (BASE_SEPOLIA_CHAIN_ID,)
    assert offering.price == Decimal("1.25")
    assert offering.currency == "USDC"


def test_live_discovery_skips_malformed_external_metadata() -> None:
    def runner(
        arguments: list[str], _timeout_seconds: int, _environment: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        payload = {
            "data": [
                {"walletAddress": "x" * 300, "name": "oversized"},
                {
                    "walletAddress": PROVIDER_ADDRESS,
                    "name": "Audit Agent",
                    "chains": [{"chainId": BASE_SEPOLIA_CHAIN_ID}],
                    "offerings": [
                        {"name": "x" * 300, "priceValue": "NaN"},
                        {"name": "Dependency Audit", "priceValue": "1.25"},
                    ],
                },
            ]
        }
        return subprocess.CompletedProcess(arguments, 0, stdout=json_text(payload), stderr="")

    providers = VirtualsLiveAdapter(runner=runner).discover_providers(
        "audit", chain_id=BASE_SEPOLIA_CHAIN_ID
    )

    assert len(providers) == 1
    assert [offering.name for offering in providers[0].offerings] == ["Dependency Audit"]


def test_live_discovery_rejects_oversized_query_before_invoking_cli() -> None:
    def unexpected_runner(
        arguments: list[str], _timeout_seconds: int, _environment: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        raise AssertionError("runner must not be invoked")

    with pytest.raises(VirtualsAdapterError, match="1 to 512"):
        VirtualsLiveAdapter(runner=unexpected_runner).discover_providers(
            "x" * 513,
            chain_id=BASE_SEPOLIA_CHAIN_ID,
        )


def test_live_history_captures_deliverable_verification_and_payment_metadata() -> None:
    def runner(
        arguments: list[str], _timeout_seconds: int, _environment: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        payload = {
            "jobId": "42",
            "chainId": BASE_SEPOLIA_CHAIN_ID,
            "status": "completed",
            "entries": [
                {
                    "kind": "system",
                    "event": {
                        "type": "budget.set",
                        "amount": 1.25,
                        "fundRequest": {"amount": 1.25, "symbol": "USDC"},
                    },
                },
                {
                    "kind": "system",
                    "event": {"type": "job.funded", "amount": 1.25},
                },
                {
                    "kind": "system",
                    "event": {
                        "type": "job.submitted",
                        "deliverable": "Audit passed: https://proof.example/result?token=private",
                    },
                },
                {
                    "kind": "system",
                    "event": {"type": "job.completed", "reason": "Verifier accepted evidence"},
                },
            ],
        }
        return subprocess.CompletedProcess(arguments, 0, stdout=json_text(payload), stderr="")

    snapshot = VirtualsLiveAdapter(runner=runner).get_job("42", chain_id=BASE_SEPOLIA_CHAIN_ID)

    assert snapshot.deliverable == "Audit passed: https://proof.example/result"
    assert snapshot.verification_result == "PASSED: Verifier accepted evidence"
    assert snapshot.payment_metadata == {
        "budget": "1.25",
        "fund_request": {"amount": "1.25", "symbol": "USDC"},
        "funded": True,
        "funded_amount": "1.25",
    }
    assert snapshot.links == ("https://proof.example/result",)


def test_live_history_rejects_non_finite_payment_metadata() -> None:
    snapshot = VirtualsLiveAdapter._snapshot(
        {"payment": {"amount": "NaN", "nested": {"budget": "Infinity"}}},
        job_id="42",
        chain_id=BASE_SEPOLIA_CHAIN_ID,
    )

    assert snapshot.payment_metadata == {
        "amount": "[INVALID DECIMAL]",
        "nested": {"budget": "[INVALID DECIMAL]"},
    }


def json_text(value: Any) -> str:
    return json.dumps(value)


def test_live_adapter_rejects_mainnet_and_non_wallet_provider() -> None:
    adapter = VirtualsLiveAdapter(
        runner=lambda arguments, _timeout, _environment: subprocess.CompletedProcess(
            arguments, 0, stdout="{}", stderr=""
        )
    )

    with pytest.raises(ValidationError, match="Base Sepolia"):
        VirtualsJobRequest.model_validate({**request().model_dump(), "chain_id": 8453})
    with pytest.raises(VirtualsAdapterError, match="EVM wallet"):
        adapter.create_job(request("agent-b"))


def test_cli_failures_are_bounded_and_secret_redacted() -> None:
    def runner(
        arguments: list[str], _timeout_seconds: int, _environment: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            arguments,
            1,
            stdout="",
            stderr=(
                "authorization=super-secret https://auth.virtuals.io/callback?token=also-secret"
            ),
        )

    adapter = VirtualsLiveAdapter(runner=runner)

    with pytest.raises(VirtualsAdapterError) as captured:
        adapter.create_job(request(PROVIDER_ADDRESS))

    message = str(captured.value)
    assert "super-secret" not in message
    assert "also-secret" not in message
    assert "[REDACTED]" in message
    assert "https://auth.virtuals.io/" in message


def test_recursive_cli_payload_redaction() -> None:
    sanitized = sanitize_cli_payload(
        {
            "accessToken": "secret-value",
            "nested": {"private_key": "0xsecret"},
            "link": "https://example.com/jobs/1?credential=secret",
        }
    )

    assert sanitized == {
        "accessToken": "[REDACTED]",
        "nested": {"private_key": "[REDACTED]"},
        "link": "https://example.com/jobs/1",
    }
