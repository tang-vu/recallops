from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from recallops.demo.common import budget, permission_grant, policy
from recallops.memory.sibyl_store import SibylMemoryStore
from recallops.models import FailureFingerprint


def test_real_sibyl_round_trip_and_explicit_close(tmp_path: Path) -> None:
    database = (tmp_path / "memory.db").resolve()
    current_session = uuid4()
    store = SibylMemoryStore(database, "tenant-a")
    store.write_policy(policy(), str(current_session))
    store.write_budget(budget(current_session))
    store.write_permission(permission_grant(current_session))
    store.write_failure(
        FailureFingerprint(
            tenant_id="recallops-demo",
            provider_id="agent-a",
            task_category="security-review",
            task_fingerprint="sha256:dependency-audit-v1",
            verifier_id="verifier-v1",
            verification_reason="Evidence missing.",
            source_session_id=current_session,
        )
    )

    context = store.load_evaluation_context(
        owner_id="vu-tang",
        requesting_agent_id="procurement-agent",
        provider_id="agent-a",
        task_category="security-review",
        task_fingerprint="sha256:dependency-audit-v1",
        permission="hire-agent",
    )
    store.close()

    assert context.policy is not None
    assert context.budget is not None
    assert context.matching_failure is not None
    database.unlink()
    assert not database.exists()


def test_tenant_isolation_uses_sibyl_schema(tmp_path: Path) -> None:
    database = (tmp_path / "memory.db").resolve()
    source_session = uuid4()
    with SibylMemoryStore(database, "tenant-a") as tenant_a:
        tenant_a.write_policy(policy(), str(source_session))
        assert (
            tenant_a.load_evaluation_context(
                owner_id="vu-tang",
                requesting_agent_id="procurement-agent",
                provider_id="agent-a",
                task_category="security-review",
                task_fingerprint="never-seen",
                permission="hire-agent",
            ).policy
            is not None
        )

    with SibylMemoryStore(database, "tenant-b") as tenant_b:
        assert (
            tenant_b.load_evaluation_context(
                owner_id="vu-tang",
                requesting_agent_id="procurement-agent",
                provider_id="agent-a",
                task_category="security-review",
                task_fingerprint="never-seen",
                permission="hire-agent",
            ).policy
            is None
        )


def test_database_path_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="absolute"):
        SibylMemoryStore(Path("relative.db"), "tenant-a")


def test_superseded_and_expired_permissions_move_to_sibyl_archive(tmp_path: Path) -> None:
    database = (tmp_path / "archive.db").resolve()
    source_session = uuid4()
    now = datetime.now(UTC)
    original = permission_grant(source_session, now)
    expired_replacement = original.model_copy(update={"expires_at": now - timedelta(seconds=1)})

    with SibylMemoryStore(database, "tenant-a") as store:
        store.write_permission(original)
        replacement_writes = store.write_permission(expired_replacement)
        lifecycle_writes = store.archive_expired_records(now)

    assert replacement_writes[0]["tier"] == "ARCHIVE"
    assert lifecycle_writes[0]["tier"] == "ARCHIVE"
    assert lifecycle_writes[1]["tier"] == "COLD"
    with sqlite3.connect(database) as connection:
        archived = connection.execute(
            "SELECT category, archive_reason FROM archived_entities ORDER BY archived_at"
        ).fetchall()
        active = connection.execute(
            "SELECT COUNT(*) FROM entities WHERE category = 'permission_grant'"
        ).fetchone()
    assert archived == [
        ("permission_grant", "Superseded hire-agent permission"),
        ("permission_grant", "Expired lifecycle record"),
    ]
    assert active == (0,)


def test_retired_counterparty_is_archived_without_deleting_failure_history(
    tmp_path: Path,
) -> None:
    database = (tmp_path / "retired-counterparty.db").resolve()
    source_session = uuid4()
    failure = FailureFingerprint(
        tenant_id="tenant-a",
        provider_id="agent-a",
        task_category="security-review",
        task_fingerprint="sha256:retired-provider",
        verifier_id="verifier-v1",
        verification_reason="Evidence missing.",
        source_session_id=source_session,
    )

    with SibylMemoryStore(database, "tenant-a") as store:
        store.write_failure(failure)
        writes = store.retire_counterparty(
            "agent-a", "security-review", "Owner retired this provider"
        )
        context = store.load_evaluation_context(
            owner_id="vu-tang",
            requesting_agent_id="procurement-agent",
            provider_id="agent-a",
            task_category="security-review",
            task_fingerprint="sha256:retired-provider",
            permission="hire-agent",
        )

    assert [write["tier"] for write in writes] == ["ARCHIVE", "COLD"]
    assert context.counterparty_profile is None
    assert context.matching_failure is not None
