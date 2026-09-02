from __future__ import annotations

from collections.abc import Callable
from typing import Any

from recallops.integrations.preflight import build_preflight_report
from recallops.integrations.virtuals import VirtualsAdapterError


class ReadyVirtuals:
    def discover_providers(self, query: str, *, chain_id: int, top_k: int = 5) -> tuple[Any, ...]:
        assert query == "dependency security audit"
        assert chain_id == 84532
        assert top_k == 5
        return ({"provider": "observed"},)


class BlockedVirtuals:
    def discover_providers(self, query: str, *, chain_id: int, top_k: int = 5) -> tuple[Any, ...]:
        raise VirtualsAdapterError("ACP CLI command failed: No active agent set")


def rpc(values: dict[str, str]) -> Callable[[str], Any]:
    return lambda method: values[method]


def test_preflight_reports_readiness_without_writes_or_signatures() -> None:
    report = build_preflight_report(
        acp_executable="unused",
        rpc_call=rpc(
            {
                "eth_chainId": "0x14a34",
                "eth_blockNumber": "0x2c22c7a",
                "eth_gasPrice": "0x5b8d80",
            }
        ),
        virtuals=ReadyVirtuals(),
    )

    assert report["base_sepolia"] == {
        "status": "READY_FOR_READS",
        "chain_id": 84532,
        "block_number": 46279802,
        "gas_price_wei": "6000000",
        "rpc": "official-public",
    }
    assert report["virtuals"]["status"] == "READY_FOR_DISCOVERY"
    assert report["virtuals"]["provider_count"] == 1
    assert report["writes_performed"] is False
    assert report["signatures_requested"] is False


def test_preflight_surfaces_wrong_chain_and_human_auth_boundary() -> None:
    report = build_preflight_report(
        acp_executable="unused",
        rpc_call=rpc({"eth_chainId": "0x2105"}),
        virtuals=BlockedVirtuals(),
    )

    assert report["base_sepolia"] == {
        "status": "UNAVAILABLE",
        "reason": "Base RPC chain ID is not 84532",
    }
    assert report["virtuals"] == {
        "status": "HUMAN_ACTION_REQUIRED",
        "reason": "ACP CLI command failed: No active agent set",
    }
