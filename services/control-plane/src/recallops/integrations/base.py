"""Viem-backed Base receipt registry boundary with an explicit live gate."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field

from recallops.models import Decision, StrictModel

LOCAL_ANVIL_CHAIN_ID = 31_337
BASE_SEPOLIA_CHAIN_ID = 84_532
MAX_CLIENT_OUTPUT_BYTES = 65_536
_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
_CLIENT_ENV_ALLOWLIST = {
    "APPDATA",
    "COMSPEC",
    "HOME",
    "LANG",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
}


class BaseAdapterError(RuntimeError):
    """A safe Base integration failure that contains no RPC or signer credentials."""


class BaseAnchorRequest(StrictModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    receipt_id: UUID
    action_id: UUID
    decision: Decision
    decision_digest: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    acp_job_reference: str | None = Field(default=None, max_length=256)


class BaseAnchorResult(StrictModel):
    chain_id: int
    contract_address: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    transaction_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    receipt_id_digest: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    decision_digest: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    acp_job_reference_digest: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    record_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    explorer_url: str | None = Field(default=None, max_length=512)
    created: bool
    verified: bool


class BasePort(Protocol):
    mode: str
    chain_id: int

    def anchor(self, request: BaseAnchorRequest) -> BaseAnchorResult: ...


ClientRunner = Callable[[list[str], str, int, Mapping[str, str]], subprocess.CompletedProcess[str]]


def _default_runner(
    arguments: list[str], input_text: str, timeout_seconds: int, environment: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        arguments,
        input=input_text,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=dict(environment),
    )


class BaseViemAdapter:
    """Call the typed viem client without a shell or private-key command arguments."""

    def __init__(
        self,
        *,
        mode: str,
        chain_id: int,
        rpc_url: str,
        contract_address: str,
        submitter: str,
        client_script: str,
        node_executable: str = "node",
        live_enabled: bool = False,
        approval_id: str | None = None,
        deployment_block: int = 0,
        runner: ClientRunner = _default_runner,
        timeout_seconds: int = 150,
    ) -> None:
        if mode not in {"LOCAL ANVIL", "BASE SEPOLIA"}:
            raise ValueError("Base mode must be LOCAL ANVIL or BASE SEPOLIA")
        expected_chain = LOCAL_ANVIL_CHAIN_ID if mode == "LOCAL ANVIL" else BASE_SEPOLIA_CHAIN_ID
        if chain_id != expected_chain:
            raise ValueError("Base mode and chain ID do not match")
        if not _ADDRESS.fullmatch(contract_address) or not _ADDRESS.fullmatch(submitter):
            raise ValueError("Base contract and submitter must be EVM addresses")
        parsed = urlsplit(rpc_url)
        if mode == "LOCAL ANVIL":
            if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
                raise ValueError("Local Anvil RPC must use loopback HTTP")
        elif parsed.scheme != "https":
            raise ValueError("Base Sepolia RPC must use HTTPS")
        if (
            not client_script
            or "\x00" in client_script
            or not node_executable
            or "\x00" in node_executable
        ):
            raise ValueError("A valid viem client command is required")
        self.mode = mode
        self.chain_id = chain_id
        self._rpc_url = rpc_url
        self._contract_address = contract_address
        self._submitter = submitter
        self._client_script = client_script
        self._node_executable = node_executable
        self._live_enabled = live_enabled
        self._approval_id = approval_id
        self._deployment_block = deployment_block
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def anchor(self, request: BaseAnchorRequest) -> BaseAnchorResult:
        if self.mode == "BASE SEPOLIA" and (
            not self._live_enabled or self._approval_id is None or len(self._approval_id) < 8
        ):
            raise BaseAdapterError(
                "Base Sepolia anchoring is disabled until explicit wallet approval is recorded"
            )
        payload = {
            "operation": "anchor",
            "receiptId": str(request.receipt_id),
            "decision": request.decision.value,
            "decisionDigest": request.decision_digest,
            "acpJobReference": request.acp_job_reference,
            "chainId": self.chain_id,
            "rpcUrl": self._rpc_url,
            "contractAddress": self._contract_address,
            "submitter": self._submitter,
            "deploymentBlock": str(self._deployment_block),
        }
        environment = {
            key: value for key, value in os.environ.items() if key.upper() in _CLIENT_ENV_ALLOWLIST
        }
        if self.mode == "BASE SEPOLIA":
            environment["RECALLOPS_ENABLE_BASE_SEPOLIA"] = "true"
            environment["RECALLOPS_BASE_APPROVAL_ID"] = self._approval_id or ""
        try:
            completed = self._runner(
                [self._node_executable, self._client_script],
                json.dumps(payload, separators=(",", ":")),
                self._timeout_seconds,
                environment,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise BaseAdapterError("The viem Base client could not be executed") from exc
        if (
            len(completed.stdout.encode()) + len(completed.stderr.encode())
            > MAX_CLIENT_OUTPUT_BYTES
        ):
            raise BaseAdapterError("The viem Base client exceeded the 64 KiB output limit")
        try:
            result: Any = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise BaseAdapterError("The viem Base client returned invalid JSON") from exc
        if (
            completed.returncode != 0
            or not isinstance(result, dict)
            or result.get("ok") is not True
        ):
            safe_error = result.get("error") if isinstance(result, dict) else None
            if safe_error not in {
                "Base Sepolia anchoring requires an explicit approval gate",
                "RPC chain ID does not match request",
                "Registry chain ID mismatch",
                "Configured submitter is not authorized by the registry",
                "Receipt digest is already anchored with conflicting content",
                "Anchor transaction reverted",
                "Receipt confirmation did not match the requested anchor",
                "Base registry operation failed",
            }:
                safe_error = "Base registry operation failed"
            raise BaseAdapterError(str(safe_error))
        transaction_hash = result.get("transactionHash")
        if not isinstance(transaction_hash, str) or not _HASH.fullmatch(transaction_hash):
            raise BaseAdapterError("No verifiable Base transaction hash was returned")
        try:
            return BaseAnchorResult.model_validate(
                {
                    "chain_id": result["chainId"],
                    "contract_address": result["contractAddress"],
                    "transaction_hash": transaction_hash,
                    "receipt_id_digest": result["receiptIdDigest"],
                    "decision_digest": result["decisionDigest"],
                    "acp_job_reference_digest": result["acpJobReferenceDigest"],
                    "record_hash": result["recordHash"],
                    "explorer_url": result.get("explorerUrl"),
                    "created": result["created"],
                    "verified": result["verified"],
                }
            )
        except (KeyError, ValueError) as exc:
            raise BaseAdapterError("The viem Base client response failed validation") from exc
