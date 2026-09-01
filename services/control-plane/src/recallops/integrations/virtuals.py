"""Virtuals ACP boundary with explicit fixture and live CLI adapters."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import Field, model_validator

from recallops.models import Money, StrictModel

BASE_SEPOLIA_CHAIN_ID = 84532
MAX_CLI_OUTPUT_BYTES = 1_048_576
MAX_REQUIREMENTS_BYTES = 65_536
_CLI_ENV_ALLOWLIST = {
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
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
}
_SENSITIVE_KEY = re.compile(
    r"(authorization|cookie|credential|mnemonic|otp|password|private.?key|secret|seed|token)",
    re.IGNORECASE,
)
_BEARER_VALUE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
_TOKEN_ASSIGNMENT = re.compile(
    r"(?i)\b(token|secret|password|private[_-]?key|authorization)\s*[:=]\s*[^\s,;]+"
)
_URL = re.compile(r"https?://[^\s\"'<>]+")
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_OTP = re.compile(r"(?i)\b(otp|one[- ]time code)\s*[:=]?\s*\d{4,10}\b")


class VirtualsAdapterError(RuntimeError):
    """A sanitized Virtuals integration failure safe to expose to the API layer."""


class VirtualsOffering(StrictModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=2_000)
    price: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=6)
    currency: str | None = Field(default=None, max_length=12)
    requirements_schema: dict[str, Any] | str | None = None


class VirtualsProvider(StrictModel):
    provider_id: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=256)
    wallet_address: str | None = Field(default=None, max_length=128)
    chain_ids: tuple[int, ...] = ()
    offerings: tuple[VirtualsOffering, ...] = ()


class VirtualsJobRequest(StrictModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    action_id: UUID
    receipt_id: UUID
    provider_id: str = Field(min_length=1, max_length=256)
    offering_name: str = Field(min_length=1, max_length=256)
    requirements: dict[str, Any]
    chain_id: int
    maximum_amount: Money
    currency: str = Field(pattern=r"^[A-Z0-9]{2,12}$")

    @model_validator(mode="after")
    def enforce_safe_live_request(self) -> VirtualsJobRequest:
        if self.chain_id != BASE_SEPOLIA_CHAIN_ID:
            raise ValueError("Virtuals live execution is restricted to Base Sepolia")
        encoded = json.dumps(self.requirements, sort_keys=True, separators=(",", ":"), default=str)
        if len(encoded.encode()) > MAX_REQUIREMENTS_BYTES:
            raise ValueError("Virtuals requirements exceed the 64 KiB limit")
        return self


class VirtualsJobSnapshot(StrictModel):
    job_id: str = Field(min_length=1, max_length=256)
    integration_mode: str = Field(pattern=r"^(FIXTURE MODE|LIVE VIRTUALS)$")
    chain_id: int
    status: str = Field(min_length=1, max_length=64)
    deliverable: str | None = Field(default=None, max_length=4_096)
    verification_result: str | None = Field(default=None, max_length=512)
    payment_metadata: dict[str, Any] = Field(default_factory=dict)
    links: tuple[str, ...] = ()
    response_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def label_fixture_job(self) -> VirtualsJobSnapshot:
        if self.integration_mode == "FIXTURE MODE" and not self.job_id.startswith("fixture:"):
            raise ValueError("Fixture Virtuals jobs require a fixture: identifier")
        if self.integration_mode == "LIVE VIRTUALS" and self.job_id.startswith("fixture:"):
            raise ValueError("Live Virtuals jobs cannot use fixture identifiers")
        return self


class VirtualsPort(Protocol):
    """Capabilities used by the policy-approved commerce orchestrator."""

    mode: str

    def discover_providers(
        self, query: str, *, chain_id: int, top_k: int = 5
    ) -> tuple[VirtualsProvider, ...]: ...

    def get_offering(
        self, provider_id: str, offering_name: str, *, chain_id: int
    ) -> VirtualsOffering: ...

    def create_job(self, request: VirtualsJobRequest) -> VirtualsJobSnapshot: ...

    def get_job(self, job_id: str, *, chain_id: int) -> VirtualsJobSnapshot: ...


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _sanitize_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "[REDACTED URL]"
    if not parsed.scheme or not parsed.netloc:
        return value
    host = parsed.hostname or "redacted.invalid"
    try:
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
    except ValueError:
        return "[REDACTED URL]"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def _sanitize_error_url(value: str) -> str:
    sanitized = _sanitize_url(value)
    if sanitized == "[REDACTED URL]":
        return sanitized
    parsed = urlsplit(sanitized)
    return urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))


def sanitize_cli_text(value: str) -> str:
    """Remove credentials and URL query fragments from a bounded CLI error summary."""

    redacted = _BEARER_VALUE.sub(r"\1[REDACTED]", value)
    redacted = _TOKEN_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    redacted = _EMAIL.sub("[REDACTED EMAIL]", redacted)
    redacted = _OTP.sub("otp=[REDACTED]", redacted)
    return _URL.sub(lambda match: _sanitize_error_url(match.group(0)), redacted)[:500]


def _sanitize_payload_text(value: str) -> str:
    redacted = _BEARER_VALUE.sub(r"\1[REDACTED]", value)
    redacted = _TOKEN_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    redacted = _EMAIL.sub("[REDACTED EMAIL]", redacted)
    redacted = _OTP.sub("otp=[REDACTED]", redacted)
    return _URL.sub(lambda match: _sanitize_url(match.group(0)), redacted)


def sanitize_cli_payload(value: Any) -> Any:
    """Recursively redact known secret fields before retaining ACP metadata."""

    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if _SENSITIVE_KEY.search(str(key))
            else sanitize_cli_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_cli_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_payload_text(value)
    return value


class VirtualsFixtureAdapter:
    """Visible deterministic ACP comparison fixture, never a live-network substitute."""

    mode = "FIXTURE MODE"

    def __init__(self) -> None:
        self._offering = VirtualsOffering(
            name="Deterministic dependency audit",
            description="Fixture deliverable used to exercise policy and verification transitions.",
            price=Decimal("1.50"),
            currency="USDC",
            requirements_schema={"type": "object"},
        )
        self._providers = {
            provider.provider_id: provider
            for provider in (
                VirtualsProvider(
                    provider_id="agent-b",
                    name="Agent B",
                    chain_ids=(BASE_SEPOLIA_CHAIN_ID,),
                    offerings=(self._offering,),
                ),
                VirtualsProvider(
                    provider_id="agent-c",
                    name="Agent C",
                    chain_ids=(BASE_SEPOLIA_CHAIN_ID,),
                    offerings=(self._offering,),
                ),
            )
        }
        self._jobs: dict[str, VirtualsJobSnapshot] = {}

    def discover_providers(
        self, query: str, *, chain_id: int, top_k: int = 5
    ) -> tuple[VirtualsProvider, ...]:
        if chain_id != BASE_SEPOLIA_CHAIN_ID or top_k < 1:
            return ()
        matches = [
            provider
            for provider in self._providers.values()
            if query.lower() in f"{provider.name} {self._offering.name}".lower()
        ]
        return tuple(matches[:top_k])

    def get_offering(
        self, provider_id: str, offering_name: str, *, chain_id: int
    ) -> VirtualsOffering:
        if (
            provider_id not in self._providers
            or offering_name != self._offering.name
            or chain_id != BASE_SEPOLIA_CHAIN_ID
        ):
            raise VirtualsAdapterError("Fixture provider or offering was not found")
        return self._offering

    def create_job(self, request: VirtualsJobRequest) -> VirtualsJobSnapshot:
        self.get_offering(request.provider_id, request.offering_name, chain_id=request.chain_id)
        job_id = f"fixture:{request.action_id}"
        snapshot = VirtualsJobSnapshot(
            job_id=job_id,
            integration_mode=self.mode,
            chain_id=request.chain_id,
            status="open",
            payment_metadata={"escrow": "not-created", "funded": False},
            response_digest=_digest(
                {
                    "job_id": job_id,
                    "mode": self.mode,
                    "request": request.model_dump(mode="json"),
                }
            ),
        )
        self._jobs[job_id] = snapshot
        return snapshot

    def get_job(self, job_id: str, *, chain_id: int) -> VirtualsJobSnapshot:
        job = self._jobs.get(job_id)
        if job is None or job.chain_id != chain_id:
            raise VirtualsAdapterError("Fixture job was not found")
        return job


CommandRunner = Callable[[list[str], int, Mapping[str, str]], subprocess.CompletedProcess[str]]


def _default_runner(
    arguments: list[str], timeout_seconds: int, environment: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        arguments,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=dict(environment),
    )


class VirtualsLiveAdapter:
    """Maintained ACP CLI adapter restricted to machine-readable Base Sepolia calls."""

    mode = "LIVE VIRTUALS"

    def __init__(
        self,
        *,
        executable: str = "acp",
        runner: CommandRunner = _default_runner,
        timeout_seconds: int = 30,
    ) -> None:
        if not executable or "\x00" in executable:
            raise ValueError("A valid ACP CLI executable is required")
        self._executable = executable
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def discover_providers(
        self, query: str, *, chain_id: int, top_k: int = 5
    ) -> tuple[VirtualsProvider, ...]:
        self._require_testnet(chain_id)
        if not 1 <= top_k <= 20:
            raise VirtualsAdapterError("Virtuals discovery top_k must be between 1 and 20")
        payload = self._run(["browse", query, "--chain-ids", str(chain_id), "--top-k", str(top_k)])
        return tuple(self._providers_from_payload(payload))

    def get_offering(
        self, provider_id: str, offering_name: str, *, chain_id: int
    ) -> VirtualsOffering:
        for provider in self.discover_providers(provider_id, chain_id=chain_id, top_k=20):
            identifiers = {provider.provider_id, provider.wallet_address}
            if provider_id not in identifiers:
                continue
            for offering in provider.offerings:
                if offering.name == offering_name:
                    return offering
        raise VirtualsAdapterError("The requested live Virtuals offering was not found")

    def create_job(self, request: VirtualsJobRequest) -> VirtualsJobSnapshot:
        self._require_testnet(request.chain_id)
        if re.fullmatch(r"0x[0-9a-fA-F]{40}", request.provider_id) is None:
            raise VirtualsAdapterError("A live Virtuals provider must be an EVM wallet address")
        payload = self._run(
            [
                "client",
                "create-job",
                "--provider",
                request.provider_id,
                "--offering-name",
                request.offering_name,
                "--requirements",
                json.dumps(request.requirements, sort_keys=True, separators=(",", ":")),
                "--chain-id",
                str(request.chain_id),
            ]
        )
        job_id = self._string_value(payload, "jobId", "job_id", "id")
        if job_id is None:
            raise VirtualsAdapterError("ACP CLI returned no live job identifier")
        return self._snapshot(payload, job_id=job_id, chain_id=request.chain_id)

    def get_job(self, job_id: str, *, chain_id: int) -> VirtualsJobSnapshot:
        self._require_testnet(chain_id)
        payload = self._run(["job", "history", "--job-id", job_id, "--chain-id", str(chain_id)])
        return self._snapshot(payload, job_id=job_id, chain_id=chain_id)

    @staticmethod
    def _require_testnet(chain_id: int) -> None:
        if chain_id != BASE_SEPOLIA_CHAIN_ID:
            raise VirtualsAdapterError("Live Virtuals calls are restricted to Base Sepolia")

    def _run(self, arguments: list[str]) -> Any:
        command = [self._executable, *arguments, "--json"]
        environment = {
            key: value for key, value in os.environ.items() if key.upper() in _CLI_ENV_ALLOWLIST
        }
        environment["IS_TESTNET"] = "true"
        try:
            completed = self._runner(command, self._timeout_seconds, environment)
        except (OSError, subprocess.SubprocessError) as exc:
            raise VirtualsAdapterError("ACP CLI could not be executed") from exc
        output_size = len(completed.stdout.encode()) + len(completed.stderr.encode())
        if output_size > MAX_CLI_OUTPUT_BYTES:
            raise VirtualsAdapterError("ACP CLI output exceeded the 1 MiB safety limit")
        if completed.returncode != 0:
            summary = sanitize_cli_text(completed.stderr or completed.stdout or "unknown error")
            raise VirtualsAdapterError(f"ACP CLI command failed: {summary}")
        payload = self._parse_json(completed.stdout)
        return sanitize_cli_payload(payload)

    @staticmethod
    def _parse_json(value: str) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            for line in reversed(value.splitlines()):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        raise VirtualsAdapterError("ACP CLI returned invalid JSON")

    @classmethod
    def _providers_from_payload(cls, payload: Any) -> list[VirtualsProvider]:
        candidates: Any = payload
        if isinstance(payload, dict):
            for key in ("agents", "providers", "results", "data"):
                if isinstance(payload.get(key), list):
                    candidates = payload[key]
                    break
        if not isinstance(candidates, list):
            raise VirtualsAdapterError("ACP discovery response had an unexpected shape")
        providers: list[VirtualsProvider] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            provider_id = cls._string_value(
                item, "walletAddress", "wallet_address", "providerAddress", "address", "id"
            )
            if provider_id is None:
                continue
            name = cls._string_value(item, "name", "agentName") or provider_id
            wallet = cls._string_value(
                item, "walletAddress", "wallet_address", "providerAddress", "address"
            )
            chain_values = item.get("chainIds", item.get("chain_ids", []))
            chain_ids = (
                tuple(int(value) for value in chain_values if str(value).isdigit())
                if isinstance(chain_values, list)
                else ()
            )
            offerings_value = item.get("offerings", [])
            offerings = (
                tuple(
                    offering
                    for raw in offerings_value
                    if isinstance(raw, dict) and (offering := cls._offering_from_payload(raw))
                )
                if isinstance(offerings_value, list)
                else ()
            )
            providers.append(
                VirtualsProvider(
                    provider_id=provider_id,
                    name=name,
                    wallet_address=wallet,
                    chain_ids=chain_ids,
                    offerings=offerings,
                )
            )
        return providers

    @classmethod
    def _offering_from_payload(cls, payload: dict[str, Any]) -> VirtualsOffering | None:
        name = cls._string_value(payload, "name", "offeringName")
        if name is None:
            return None
        raw_price = payload.get("priceValue", payload.get("price"))
        try:
            price = Decimal(str(raw_price)) if raw_price is not None else None
        except InvalidOperation:
            price = None
        requirements = payload.get("requirements", payload.get("requirementSchema"))
        if not isinstance(requirements, (dict, str)):
            requirements = None
        return VirtualsOffering(
            name=name,
            description=cls._string_value(payload, "description"),
            price=price,
            currency=cls._string_value(payload, "currency", "priceCurrency"),
            requirements_schema=requirements,
        )

    @classmethod
    def _snapshot(cls, payload: Any, *, job_id: str, chain_id: int) -> VirtualsJobSnapshot:
        mapping = payload if isinstance(payload, dict) else {}
        status = cls._string_value(mapping, "status", "jobStatus") or "open"
        deliverable = cls._string_value(mapping, "deliverable", "result")
        verification = cls._string_value(
            mapping, "verificationResult", "verification_result", "evaluation"
        )
        payment = mapping.get("payment", mapping.get("escrow", {}))
        if not isinstance(payment, dict):
            payment = {"status": str(payment)}
        links = tuple(cls._collect_links(mapping))
        return VirtualsJobSnapshot(
            job_id=job_id,
            integration_mode=cls.mode,
            chain_id=chain_id,
            status=status,
            deliverable=deliverable,
            verification_result=verification,
            payment_metadata=payment,
            links=links,
            response_digest=_digest(payload),
        )

    @staticmethod
    def _string_value(mapping: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = mapping.get(key)
            if value is not None and str(value):
                return str(value)
        nested = mapping.get("data")
        if isinstance(nested, dict):
            return VirtualsLiveAdapter._string_value(nested, *keys)
        return None

    @staticmethod
    def _collect_links(value: Any) -> list[str]:
        links: list[str] = []
        if isinstance(value, dict):
            for item in value.values():
                links.extend(VirtualsLiveAdapter._collect_links(item))
        elif isinstance(value, list):
            for item in value:
                links.extend(VirtualsLiveAdapter._collect_links(item))
        elif isinstance(value, str) and value.startswith(("https://", "http://")):
            links.append(_sanitize_url(value))
        return list(dict.fromkeys(links))[:10]
