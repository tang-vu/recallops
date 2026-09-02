"""Read-only partner readiness checks that never sign or create economic actions."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from recallops.integrations.virtuals import (
    BASE_SEPOLIA_CHAIN_ID,
    VirtualsAdapterError,
    VirtualsLiveAdapter,
)

BASE_SEPOLIA_PUBLIC_RPC = "https://sepolia.base.org"
MAX_RPC_RESPONSE_BYTES = 65_536

RpcCall = Callable[[str], Any]


class ProviderDiscovery(Protocol):
    def discover_providers(
        self, query: str, *, chain_id: int, top_k: int = 5
    ) -> tuple[Any, ...]: ...


def _public_rpc_call(method: str) -> Any:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": []},
        separators=(",", ":"),
    ).encode()
    request = Request(
        BASE_SEPOLIA_PUBLIC_RPC,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "RecallOps/0.1 (+https://github.com/tang-vu/recallops)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed HTTPS endpoint
            raw_response = response.read(MAX_RPC_RESPONSE_BYTES + 1)
        if len(raw_response) > MAX_RPC_RESPONSE_BYTES:
            raise RuntimeError("Base Sepolia public RPC response exceeded 64 KiB")
        payload: Any = json.loads(raw_response)
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError) as exc:
        raise RuntimeError("Base Sepolia public RPC is unavailable") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Base Sepolia public RPC returned invalid JSON") from exc
    if not isinstance(payload, dict) or "result" not in payload or payload.get("error"):
        raise RuntimeError("Base Sepolia public RPC returned an invalid response")
    return payload["result"]


def _hex_quantity(value: Any, label: str) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise RuntimeError(f"Base Sepolia RPC returned an invalid {label}")
    try:
        return int(value, 16)
    except ValueError as exc:
        raise RuntimeError(f"Base Sepolia RPC returned an invalid {label}") from exc


def build_preflight_report(
    *,
    acp_executable: str,
    query: str = "dependency security audit",
    rpc_call: RpcCall = _public_rpc_call,
    virtuals: ProviderDiscovery | None = None,
) -> dict[str, Any]:
    """Observe public RPC and read-only ACP discovery without changing external state."""

    writes_performed = False
    try:
        chain_id = _hex_quantity(rpc_call("eth_chainId"), "chain ID")
        if chain_id != BASE_SEPOLIA_CHAIN_ID:
            raise RuntimeError("Base RPC chain ID is not 84532")
        block_number = _hex_quantity(rpc_call("eth_blockNumber"), "block number")
        gas_price = _hex_quantity(rpc_call("eth_gasPrice"), "gas price")
        base: dict[str, Any] = {
            "status": "READY_FOR_READS",
            "chain_id": chain_id,
            "block_number": block_number,
            "gas_price_wei": str(gas_price),
            "rpc": "official-public",
        }
    except RuntimeError as exc:
        base = {"status": "UNAVAILABLE", "reason": str(exc)}

    adapter = virtuals or VirtualsLiveAdapter(executable=acp_executable)
    try:
        providers = adapter.discover_providers(
            query,
            chain_id=BASE_SEPOLIA_CHAIN_ID,
            top_k=5,
        )
        virtuals_result: dict[str, Any] = {
            "status": "READY_FOR_DISCOVERY",
            "provider_count": len(providers),
            "query": query,
        }
    except VirtualsAdapterError as exc:
        virtuals_result = {
            "status": "HUMAN_ACTION_REQUIRED",
            "reason": str(exc),
        }

    return {
        "base_sepolia": base,
        "virtuals": virtuals_result,
        "writes_performed": writes_performed,
        "signatures_requested": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run read-only Base Sepolia and Virtuals ACP readiness checks."
    )
    parser.add_argument("--acp-executable", default="acp")
    parser.add_argument("--query", default="dependency security audit")
    arguments = parser.parse_args()
    report = build_preflight_report(
        acp_executable=arguments.acp_executable,
        query=arguments.query,
    )
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
