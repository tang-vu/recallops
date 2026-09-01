"""Shared process metadata and demo fixtures."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from recallops.models import BudgetAccount, OwnerPolicy, PermissionGrant, ProposedAction

DEMO_TENANT = "recallops-demo"
DEMO_OWNER = "vu-tang"
DEMO_AGENT = "procurement-agent"
TASK_CATEGORY = "security-review"
TASK_FINGERPRINT = "sha256:dependency-audit-v1"


def session_id() -> UUID:
    return uuid4()


def process_metadata(current_session_id: UUID) -> dict[str, str | int]:
    return {
        "session_id": str(current_session_id),
        "process_id": os.getpid(),
        "utc_timestamp": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
    }


def git_commit() -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        return "unavailable"
    try:
        return subprocess.run(  # noqa: S603
            [git_executable, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def policy(now: datetime | None = None) -> OwnerPolicy:
    current = now or datetime.now(UTC) - timedelta(minutes=1)
    return OwnerPolicy(
        tenant_id=DEMO_TENANT,
        owner_id=DEMO_OWNER,
        version="demo-policy-v1",
        per_action_limit=Decimal("2.00"),
        cumulative_budget=Decimal("5.00"),
        window_started_at=current,
        window_ends_at=current + timedelta(days=1),
    )


def budget(current_session_id: UUID, now: datetime | None = None) -> BudgetAccount:
    active_policy = policy(now)
    return BudgetAccount(
        tenant_id=DEMO_TENANT,
        owner_id=DEMO_OWNER,
        currency="USDC",
        spent=Decimal("0.00"),
        window_started_at=active_policy.window_started_at,
        window_ends_at=active_policy.window_ends_at,
        source_session_id=current_session_id,
    )


def permission_grant(current_session_id: UUID, now: datetime | None = None) -> PermissionGrant:
    current = now or datetime.now(UTC) - timedelta(minutes=1)
    return PermissionGrant(
        tenant_id=DEMO_TENANT,
        owner_id=DEMO_OWNER,
        requesting_agent_id=DEMO_AGENT,
        permission="hire-agent",
        provider_id=None,
        task_categories=(TASK_CATEGORY,),
        valid_from=current,
        expires_at=current + timedelta(days=1),
        source_session_id=current_session_id,
    )


def action(provider_id: str, current_session_id: UUID) -> ProposedAction:
    return ProposedAction(
        tenant_id=DEMO_TENANT,
        owner_id=DEMO_OWNER,
        requesting_agent_id=DEMO_AGENT,
        provider_id=provider_id,
        offering="Deterministic dependency audit",
        task_category=TASK_CATEGORY,
        task_fingerprint=TASK_FINGERPRINT,
        requested_amount=Decimal("1.00") if provider_id == "agent-a" else Decimal("1.50"),
        currency="USDC",
        chain="base-sepolia",
        session_id=current_session_id,
        required_verifier="deterministic-schema-verifier-v1",
        risk_class="MEDIUM",
        permission="hire-agent",
        rationale=(
            "Prefer Agent A because it is cheaper."
            if provider_id == "agent-a"
            else "Use Agent B after Agent A is rejected by durable policy memory."
        ),
    )


def resolve_database(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if path.suffix != ".db":
        raise ValueError("Demo database path must end in .db")
    return path
