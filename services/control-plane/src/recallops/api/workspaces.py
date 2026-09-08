"""Authenticated, isolated workspaces for the developer decision gateway.

SQLite holds credential hashes and configuration metadata; all policy, failure,
and decision memory still goes through Sibyl. The registry transaction serializes
workspace changes and evaluation replays across worker processes.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Header, HTTPException
from pydantic import AwareDatetime, Field, model_validator

from recallops.memory.port import MemorySubsystemError
from recallops.memory.sibyl_store import SibylMemoryStore
from recallops.models import (
    BudgetAccount,
    DecisionReceipt,
    EvaluationContext,
    FailureFingerprint,
    IdempotencyRecord,
    Money,
    OwnerPolicy,
    PermissionGrant,
    ProposedAction,
    StrictModel,
    utc_now,
)
from recallops.orchestration.execution import request_digest
from recallops.orchestration.guard import CommerceGuard
from recallops.policy.engine import PolicyEngine


class WorkspaceCreate(StrictModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    agent_id: str = Field(default="my-agent", pattern=r"^[a-zA-Z0-9_-]{1,64}$")


class WorkspacePolicy(StrictModel):
    per_action_limit: Money = Decimal("10")
    cumulative_budget: Money = Decimal("100")
    recorded_spend: Money = Decimal("0")
    currency: str = Field(default="USDC", pattern=r"^[A-Z0-9]{2,12}$")
    chain: str = Field(default="base-sepolia", min_length=1, max_length=64)
    permission: str = Field(default="hire-agent", min_length=1, max_length=128)
    task_categories: tuple[str, ...] = Field(default=("security-review",), max_length=30)
    prohibited_providers: tuple[str, ...] = Field(default=(), max_length=100)
    require_verifier: bool = True
    high_risk_requires_human: bool = True
    agent_enabled: bool = True
    window_ends_at: AwareDatetime = Field(default_factory=lambda: utc_now() + timedelta(days=30))

    @model_validator(mode="after")
    def valid_limits(self) -> WorkspacePolicy:
        if self.per_action_limit > self.cumulative_budget:
            raise ValueError("Per-action limit cannot exceed the cumulative budget.")
        for value in (*self.task_categories, *self.prohibited_providers):
            if not value.strip() or len(value) > 128:
                raise ValueError("Categories and provider IDs must contain 1 to 128 characters.")
        return self


class GatewayAction(StrictModel):
    provider_id: str = Field(min_length=1, max_length=128)
    offering: str = Field(min_length=1, max_length=256)
    task_category: str = Field(min_length=1, max_length=128)
    task_fingerprint: str = Field(min_length=1, max_length=256)
    requested_amount: Money
    currency: str = Field(default="USDC", pattern=r"^[A-Z0-9]{2,12}$")
    chain: str = Field(default="base-sepolia", min_length=1, max_length=64)
    permission: str = Field(default="hire-agent", min_length=1, max_length=128)
    required_verifier: str | None = Field(default=None, min_length=1, max_length=128)
    risk_class: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    rationale: str | None = Field(default=None, max_length=2000)


class FailureReport(StrictModel):
    provider_id: str = Field(min_length=1, max_length=128)
    task_category: str = Field(min_length=1, max_length=128)
    task_fingerprint: str = Field(min_length=1, max_length=256)
    verifier_id: str = Field(min_length=1, max_length=128)
    verification_reason: str = Field(min_length=1, max_length=512)


def digest_key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class WorkspaceEngine(PolicyEngine):
    """Stable receipt identity lets retries recover an interrupted replay-index write."""

    def evaluate(self, action: ProposedAction, context: EvaluationContext) -> DecisionReceipt:
        receipt = super().evaluate(action, context)
        return receipt.model_copy(update={"receipt_id": uuid5(action.action_id, "decision")})


def workspace_router(root: Path | None) -> APIRouter:
    router = APIRouter(prefix="/v1/workspace", tags=["Developer workspace"])

    @contextmanager
    def registry() -> Iterator[sqlite3.Connection]:
        if root is None:
            raise HTTPException(503, "Workspace storage is not configured.")
        root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(root / "workspaces.sqlite3", timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS workspaces ("
                "id TEXT PRIMARY KEY, name TEXT NOT NULL, agent_id TEXT NOT NULL, "
                "owner_hash TEXT UNIQUE NOT NULL, agent_hash TEXT UNIQUE NOT NULL, "
                "config TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS rate_limits "
                "(bucket TEXT PRIMARY KEY, count INTEGER NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS policy_updates (workspace_id TEXT PRIMARY KEY)"
            )
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except MemorySubsystemError as exc:
            connection.rollback()
            raise HTTPException(
                503, "Durable memory unavailable. Stop the action and retry later."
            ) from exc
        except sqlite3.Error as exc:
            connection.rollback()
            raise HTTPException(
                503, "Workspace storage is busy or unavailable. Retry later."
            ) from exc
        finally:
            connection.close()

    def rate_limit(
        db: sqlite3.Connection, subject: str, maximum: int, *, hourly: bool = False
    ) -> None:
        period = utc_now().strftime("%Y%m%d%H" if hourly else "%Y%m%d%H%M")
        bucket = f"{subject}:{period}"
        row = db.execute("SELECT count FROM rate_limits WHERE bucket = ?", (bucket,)).fetchone()
        if row and row["count"] >= maximum:
            raise HTTPException(429, "Request limit reached. Retry in the next time window.")
        db.execute(
            "DELETE FROM rate_limits WHERE bucket LIKE ? AND bucket != ?", (f"{subject}:%", bucket)
        )
        db.execute(
            "INSERT INTO rate_limits VALUES (?, 1) "
            "ON CONFLICT(bucket) DO UPDATE SET count = count + 1",
            (bucket,),
        )

    def authenticate(
        db: sqlite3.Connection, authorization: str | None, *, owner: bool = True
    ) -> sqlite3.Row:
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 200:
            raise HTTPException(401, "A workspace bearer key is required.")
        key_hash = digest_key(authorization[7:])
        row = db.execute(
            "SELECT * FROM workspaces WHERE owner_hash = ? OR agent_hash = ?",
            (key_hash, key_hash),
        ).fetchone()
        if row is None:
            raise HTTPException(401, "Workspace key is invalid or revoked.")
        if owner and not secrets.compare_digest(row["owner_hash"], key_hash):
            raise HTTPException(403, "This operation requires the workspace owner key.")
        rate_limit(db, row["id"], 120)
        return cast(sqlite3.Row, row)

    def memory_for(row: sqlite3.Row | dict[str, str]) -> SibylMemoryStore:
        assert root is not None
        # ID originates only from server-generated UUIDs, never a client path.
        workspace_id = str(UUID(row["id"]))
        return SibylMemoryStore(root / f"{workspace_id}.db", workspace_id)

    def write_config(row: sqlite3.Row | dict[str, str], config: WorkspacePolicy) -> None:
        now = utc_now()
        if config.window_ends_at <= now:
            raise HTTPException(422, "The budget window must end in the future.")
        session = uuid4()
        started = datetime.fromisoformat(row["created_at"])
        with memory_for(row) as memory:
            memory.write_policy(
                OwnerPolicy(
                    tenant_id=row["id"],
                    owner_id="owner",
                    version=str(uuid4()),
                    currency=config.currency,
                    chain=config.chain,
                    per_action_limit=config.per_action_limit,
                    cumulative_budget=config.cumulative_budget,
                    window_started_at=started,
                    window_ends_at=config.window_ends_at,
                    require_verifier=config.require_verifier,
                    high_risk_requires_human=config.high_risk_requires_human,
                    prohibited_providers=config.prohibited_providers,
                ),
                str(session),
            )
            memory.write_budget(
                BudgetAccount(
                    tenant_id=row["id"],
                    owner_id="owner",
                    currency=config.currency,
                    spent=config.recorded_spend,
                    window_started_at=started,
                    window_ends_at=config.window_ends_at,
                    source_session_id=session,
                )
            )
            memory.write_permission(
                PermissionGrant(
                    tenant_id=row["id"],
                    owner_id="owner",
                    requesting_agent_id=row["agent_id"],
                    permission=config.permission,
                    task_categories=config.task_categories,
                    valid_from=started,
                    expires_at=config.window_ends_at,
                    source_session_id=session,
                    revoked_at=None if config.agent_enabled else now,
                    revocation_reason=None if config.agent_enabled else "Paused by workspace owner",
                )
            )

    @router.post("", status_code=201)
    def create_workspace(payload: WorkspaceCreate) -> dict[str, Any]:
        owner_key = f"ro_owner_{secrets.token_urlsafe(32)}"
        agent_key = f"ro_agent_{secrets.token_urlsafe(32)}"
        row = {
            "id": str(uuid4()),
            "name": payload.name.strip(),
            "agent_id": payload.agent_id,
            "created_at": utc_now().isoformat(),
        }
        config = WorkspacePolicy()
        with registry() as db:
            rate_limit(db, "create", 10, hourly=True)
            write_config(row, config)
            db.execute(
                "INSERT INTO workspaces VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    row["id"],
                    row["name"],
                    row["agent_id"],
                    digest_key(owner_key),
                    digest_key(agent_key),
                    config.model_dump_json(),
                    row["created_at"],
                ),
            )
        return {"workspace": row, "owner_key": owner_key, "agent_key": agent_key}

    @router.get("")
    def get_workspace(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
        with registry() as db:
            row = authenticate(db, authorization)
            with memory_for(row) as memory:
                healthy = bool(memory.health()["healthy"])
            return {
                "id": row["id"],
                "name": row["name"],
                "agent_id": row["agent_id"],
                "created_at": row["created_at"],
                "policy": json.loads(row["config"]),
                "memory_healthy": healthy,
            }

    @router.put("/policy")
    def save_policy(
        payload: WorkspacePolicy, authorization: Annotated[str | None, Header()] = None
    ) -> dict[str, Any]:
        with registry() as db:
            row = authenticate(db, authorization)
            previous = WorkspacePolicy.model_validate_json(row["config"])
            # A permission rename would leave the old grant active. Keep one fixed
            # permission for this single-agent workspace until grant management exists.
            if payload.permission != previous.permission:
                raise HTTPException(422, "The workspace permission cannot be renamed.")
            if payload.window_ends_at <= utc_now():
                raise HTTPException(422, "The budget window must end in the future.")
            # Sibyl and the identity registry use separate databases. Commit a
            # durable stop marker first so an interrupted multi-record update
            # cannot leave the gateway approving against partially saved policy.
            db.execute("INSERT OR IGNORE INTO policy_updates VALUES (?)", (row["id"],))
            db.commit()
            db.execute("BEGIN IMMEDIATE")
            write_config(row, payload)
            db.execute(
                "UPDATE workspaces SET config = ? WHERE id = ?",
                (payload.model_dump_json(), row["id"]),
            )
            db.execute("DELETE FROM policy_updates WHERE workspace_id = ?", (row["id"],))
        return {"policy": payload.model_dump(mode="json")}

    @router.post("/keys/rotate")
    def rotate_key(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
        key = f"ro_agent_{secrets.token_urlsafe(32)}"
        with registry() as db:
            row = authenticate(db, authorization)
            db.execute(
                "UPDATE workspaces SET agent_hash = ? WHERE id = ?", (digest_key(key), row["id"])
            )
        return {"agent_key": key}

    @router.get("/decisions")
    def decisions(authorization: Annotated[str | None, Header()] = None) -> list[dict[str, Any]]:
        with registry() as db:
            row = authenticate(db, authorization)
            with memory_for(row) as memory:
                receipts = sorted(
                    memory.list_decisions(100), key=lambda item: item.created_at, reverse=True
                )
                return [
                    {
                        "receipt": receipt.model_dump(mode="json"),
                        "action": action.model_dump(mode="json")
                        if (action := memory.get_proposed_action(str(receipt.action_id)))
                        else None,
                    }
                    for receipt in receipts
                ]

    @router.post("/failures", status_code=201)
    def report_failure(
        payload: FailureReport, authorization: Annotated[str | None, Header()] = None
    ) -> dict[str, Any]:
        with registry() as db:
            row = authenticate(db, authorization)
            with memory_for(row) as memory:
                writes = memory.write_failure(
                    FailureFingerprint(
                        tenant_id=row["id"],
                        source_session_id=uuid4(),
                        **payload.model_dump(),
                    )
                )
        return {"writes": writes}

    @router.post("/evaluate")
    def evaluate(
        payload: GatewayAction,
        idempotency_key: Annotated[str, Header(min_length=8, max_length=128)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        with registry() as db:
            row = authenticate(db, authorization, owner=False)
            if db.execute(
                "SELECT 1 FROM policy_updates WHERE workspace_id = ?", (row["id"],)
            ).fetchone():
                raise HTTPException(
                    503, "Policy update is incomplete. The owner must save policy again."
                )
            if not WorkspacePolicy.model_validate_json(row["config"]).agent_enabled:
                raise HTTPException(403, "Agent access is paused by the workspace owner.")
            key_hash = digest_key(idempotency_key)
            body_hash = request_digest(payload.model_dump(mode="json"))
            action_id = uuid5(NAMESPACE_URL, f"{row['id']}:{key_hash}")
            with memory_for(row) as memory:
                prior = memory.get_idempotency_record("workspace-evaluate", key_hash)
                if prior:
                    if prior.request_digest != body_hash:
                        raise HTTPException(
                            409, "Idempotency key already belongs to a different request."
                        )
                    receipt = memory.get_decision(prior.result_reference)
                    if receipt is None:
                        raise MemorySubsystemError("Missing replay receipt")
                    return {"receipt": receipt.model_dump(mode="json"), "idempotent_replay": True}
                # Recover when Sibyl persisted the receipt but the process exited
                # before the idempotency index was written. Never evaluate again
                # with changed memory or create a second receipt for that action.
                recovered = memory.get_decision(str(uuid5(action_id, "decision")))
                if recovered is not None:
                    original = memory.get_proposed_action(str(action_id))
                    if original is None:
                        raise MemorySubsystemError("Replay action is missing")
                    original_body = GatewayAction.model_validate(
                        {name: getattr(original, name) for name in GatewayAction.model_fields}
                    )
                    if request_digest(original_body.model_dump(mode="json")) != body_hash:
                        raise HTTPException(
                            409, "Idempotency key already belongs to a different request."
                        )
                    memory.write_idempotency_record(
                        IdempotencyRecord(
                            tenant_id=row["id"],
                            operation="workspace-evaluate",
                            key_digest=key_hash,
                            request_digest=body_hash,
                            result_reference=str(recovered.receipt_id),
                        )
                    )
                    return {"receipt": recovered.model_dump(mode="json"), "idempotent_replay": True}
                action = ProposedAction(
                    action_id=action_id,
                    tenant_id=row["id"],
                    owner_id="owner",
                    requesting_agent_id=row["agent_id"],
                    session_id=uuid4(),
                    **payload.model_dump(),
                )
                receipt, writes = CommerceGuard(memory, WorkspaceEngine()).evaluate(action)
                if writes:
                    memory.write_idempotency_record(
                        IdempotencyRecord(
                            tenant_id=row["id"],
                            operation="workspace-evaluate",
                            key_digest=key_hash,
                            request_digest=body_hash,
                            result_reference=str(receipt.receipt_id),
                        )
                    )
                return {"receipt": receipt.model_dump(mode="json"), "idempotent_replay": False}

    return router
