from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from recallops.api.app import create_app
from recallops.memory.port import MemorySubsystemError
from recallops.memory.sibyl_store import SibylMemoryStore

ACTION = {
    "provider_id": "real-provider",
    "offering": "Dependency audit",
    "task_category": "security-review",
    "task_fingerprint": "audit:v1",
    "requested_amount": "1.00",
    "currency": "USDC",
    "chain": "base-sepolia",
    "permission": "hire-agent",
    "required_verifier": "schema-check-v1",
}


def create(client: TestClient, name: str = "Test workspace") -> dict[str, Any]:
    response = client.post("/v1/workspace", json={"name": name, "agent_id": "my-agent"})
    assert response.status_code == 201, response.text
    return dict(response.json())


def auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def evaluate(
    client: TestClient, key: str, body: dict[str, Any] | None = None, idempotency: str | None = None
) -> Any:
    return client.post(
        "/v1/workspace/evaluate",
        headers={
            **auth(key),
            "Idempotency-Key": idempotency or str(uuid4()),
        },
        json=body or ACTION,
    )


def test_workspace_keys_scope_isolation_and_restart(tmp_path: Path) -> None:
    database = tmp_path / "demo.db"
    client = TestClient(create_app(memory_db=database))
    first, second = create(client), create(client, "Other workspace")
    assert client.get("/v1/workspace").status_code == 401
    assert client.get("/v1/workspace", headers=auth(first["agent_key"])).status_code == 403
    assert (
        client.get("/v1/workspace", headers=auth(first["owner_key"])).json()["name"]
        == "Test workspace"
    )
    receipt = evaluate(client, first["agent_key"]).json()["receipt"]
    assert receipt["decision"] == "APPROVE"
    assert receipt["tenant_id"] == first["workspace"]["id"]
    assert client.get("/v1/workspace/decisions", headers=auth(second["owner_key"])).json() == []
    assert client.get("/v1/decisions", params={"tenant_id": first["workspace"]["id"]}).json() == []
    restarted = TestClient(create_app(memory_db=database))
    history = restarted.get("/v1/workspace/decisions", headers=auth(first["owner_key"])).json()
    assert history[0]["receipt"]["receipt_id"] == receipt["receipt_id"]
    assert history[0]["action"]["provider_id"] == ACTION["provider_id"]
    raw = (tmp_path / "workspaces" / "workspaces.sqlite3").read_bytes()
    assert first["owner_key"].encode() not in raw
    assert first["agent_key"].encode() not in raw


def test_real_failure_changes_future_decision(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    assert evaluate(client, keys["agent_key"]).json()["receipt"]["decision"] == "APPROVE"
    failure = {
        "provider_id": ACTION["provider_id"],
        "task_category": ACTION["task_category"],
        "task_fingerprint": ACTION["task_fingerprint"],
        "verifier_id": "schema-check-v1",
        "verification_reason": "Required dependency evidence missing.",
    }
    assert (
        client.post(
            "/v1/workspace/failures", headers=auth(keys["agent_key"]), json=failure
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/v1/workspace/failures", headers=auth(keys["owner_key"]), json=failure
        ).status_code
        == 201
    )
    receipt = evaluate(client, keys["agent_key"]).json()["receipt"]
    assert receipt["decision"] == "DENY"
    assert "REPEATED_FAILURE_FINGERPRINT" in receipt["reason_codes"]
    assert any(item["record_type"] == "failure_fingerprint" for item in receipt["memory_evidence"])
    assert (
        evaluate(client, keys["agent_key"], {**ACTION, "provider_id": "other"}).json()["receipt"][
            "decision"
        ]
        == "APPROVE"
    )


def test_policy_changes_pause_and_rotation(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    owner = auth(keys["owner_key"])
    config = client.get("/v1/workspace", headers=owner).json()["policy"]
    config["per_action_limit"] = "0.50"
    assert (
        client.put("/v1/workspace/policy", headers=auth(keys["agent_key"]), json=config).status_code
        == 403
    )
    assert client.put("/v1/workspace/policy", headers=owner, json=config).status_code == 200
    assert (
        "PER_ACTION_LIMIT_EXCEEDED"
        in evaluate(client, keys["agent_key"]).json()["receipt"]["reason_codes"]
    )
    config["agent_enabled"] = False
    assert client.put("/v1/workspace/policy", headers=owner, json=config).status_code == 200
    assert evaluate(client, keys["agent_key"]).status_code == 403
    replacement = client.post("/v1/workspace/keys/rotate", headers=owner).json()["agent_key"]
    assert evaluate(client, keys["agent_key"]).status_code == 401
    config["agent_enabled"] = True
    config["per_action_limit"] = "10"
    config["recorded_spend"] = "99.50"
    assert client.put("/v1/workspace/policy", headers=owner, json=config).status_code == 200
    assert (
        "CUMULATIVE_BUDGET_EXCEEDED"
        in evaluate(client, replacement).json()["receipt"]["reason_codes"]
    )


def test_replays_conflicts_and_concurrent_duplicates(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    identifier = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: evaluate(client, keys["agent_key"], idempotency=identifier), range(2)
            )
        )
    assert all(response.status_code == 200 for response in responses)
    assert {response.json()["idempotent_replay"] for response in responses} == {False, True}
    assert len({response.json()["receipt"]["receipt_id"] for response in responses}) == 1
    conflict = evaluate(client, keys["agent_key"], {**ACTION, "requested_amount": "2"}, identifier)
    assert conflict.status_code == 409
    assert len(client.get("/v1/workspace/decisions", headers=auth(keys["owner_key"])).json()) == 1


def test_client_cannot_override_identity_or_policy_time(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    for field, value in [
        ("tenant_id", "other"),
        ("owner_id", "other"),
        ("requesting_agent_id", "other"),
        ("proposed_at", "2026-01-01T00:00:00Z"),
    ]:
        assert evaluate(client, keys["agent_key"], {**ACTION, field: value}).status_code == 422
    assert (
        client.post(
            "/v1/workspace/evaluate", headers=auth(keys["agent_key"]), json=ACTION
        ).status_code
        == 422
    )


def test_interrupted_policy_update_stays_closed_until_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    owner = auth(keys["owner_key"])
    config = client.get("/v1/workspace", headers=owner).json()["policy"]
    original = SibylMemoryStore.write_budget

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise MemorySubsystemError("Injected failure")

    monkeypatch.setattr(SibylMemoryStore, "write_budget", broken)
    assert client.put("/v1/workspace/policy", headers=owner, json=config).status_code == 503
    assert evaluate(client, keys["agent_key"]).status_code == 503
    restarted = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    assert evaluate(restarted, keys["agent_key"]).status_code == 503
    monkeypatch.setattr(SibylMemoryStore, "write_budget", original)
    assert restarted.put("/v1/workspace/policy", headers=owner, json=config).status_code == 200
    assert evaluate(restarted, keys["agent_key"]).json()["receipt"]["decision"] == "APPROVE"


def test_missing_memory_does_not_approve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise MemorySubsystemError("Injected failure")

    monkeypatch.setattr(SibylMemoryStore, "load_evaluation_context", broken)
    result = evaluate(client, keys["agent_key"]).json()
    assert result["receipt"]["decision"] == "ESCALATE"


def test_workspace_creation_limit_is_durable(tmp_path: Path) -> None:
    import sqlite3

    from recallops.models import utc_now

    database = tmp_path / "demo.db"
    client = TestClient(create_app(memory_db=database))
    create(client)
    with sqlite3.connect(tmp_path / "workspaces" / "workspaces.sqlite3") as db:
        db.execute(
            "UPDATE rate_limits SET count = 10 WHERE bucket = ?", (f"create:{utc_now():%Y%m%d%H}",)
        )
    restarted = TestClient(create_app(memory_db=database))
    assert restarted.post("/v1/workspace", json={"name": "Over limit"}).status_code == 429


def test_retry_recovers_receipt_after_interrupted_idempotency_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    identifier = str(uuid4())
    original = SibylMemoryStore.write_idempotency_record

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise MemorySubsystemError("Injected index write failure")

    monkeypatch.setattr(SibylMemoryStore, "write_idempotency_record", broken)
    assert evaluate(client, keys["agent_key"], idempotency=identifier).status_code == 503
    history = client.get("/v1/workspace/decisions", headers=auth(keys["owner_key"])).json()
    assert len(history) == 1
    monkeypatch.setattr(SibylMemoryStore, "write_idempotency_record", original)
    assert (
        evaluate(
            client, keys["agent_key"], {**ACTION, "requested_amount": "2"}, identifier
        ).status_code
        == 409
    )
    recovered = evaluate(client, keys["agent_key"], idempotency=identifier).json()
    assert recovered["idempotent_replay"] is True
    assert recovered["receipt"]["receipt_id"] == history[0]["receipt"]["receipt_id"]
    assert len(client.get("/v1/workspace/decisions", headers=auth(keys["owner_key"])).json()) == 1
