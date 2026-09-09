from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from recallops.api.app import create_app
from recallops.memory.port import MemorySubsystemError
from recallops.memory.sibyl_store import SibylMemoryStore
from recallops.models import utc_now

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


def test_owner_review_is_scoped_durable_and_requires_current_authorization(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys, other = create(client), create(client, "Other")
    receipt = evaluate(client, keys["agent_key"], {**ACTION, "risk_class": "HIGH"}).json()[
        "receipt"
    ]
    assert receipt["reason_codes"] == ["HUMAN_APPROVAL_REQUIRED"]
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
    body = {"decision": "APPROVE", "reason": "Reviewed the task and accepted this risk."}
    assert (
        client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()["allowed_now"]
        is False
    )
    assert (
        client.post(route + "/review", headers=auth(keys["agent_key"]), json=body).status_code
        == 403
    )
    assert (
        client.post(route + "/review", headers=auth(other["owner_key"]), json=body).status_code
        == 404
    )
    assert client.get(route + "/authorization", headers=auth(other["agent_key"])).status_code == 404
    response = client.post(route + "/review", headers=auth(keys["owner_key"]), json=body)
    assert response.status_code == 200
    assert response.json()["review"]["expires_at"] == receipt["expires_at"]
    assert (
        client.post(route + "/review", headers=auth(keys["owner_key"]), json=body).json()[
            "idempotent_replay"
        ]
        is True
    )
    restarted = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    permit = restarted.get(route + "/authorization", headers=auth(keys["agent_key"])).json()
    assert permit["allowed_now"] is True
    assert permit["action_id"] == receipt["action_id"]
    historical = restarted.get("/v1/workspace/decisions", headers=auth(keys["owner_key"])).json()[0]
    assert historical["receipt"]["decision"] == "ESCALATE"
    assert historical["review"]["decision"] == "APPROVE"
    assert historical["review"]["reviewed_by"] == "owner"


def test_new_failure_invalidates_previously_approved_review(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    receipt = evaluate(client, keys["agent_key"], {**ACTION, "risk_class": "HIGH"}).json()[
        "receipt"
    ]
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
    assert (
        client.post(
            route + "/review",
            headers=auth(keys["owner_key"]),
            json={"decision": "APPROVE", "reason": "Reviewed."},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/v1/workspace/failures",
            headers=auth(keys["owner_key"]),
            json={
                "provider_id": ACTION["provider_id"],
                "task_category": ACTION["task_category"],
                "task_fingerprint": ACTION["task_fingerprint"],
                "verifier_id": "checker",
                "verification_reason": "New verified failure after review.",
            },
        ).status_code
        == 201
    )
    permit = client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()
    assert permit["allowed_now"] is False
    assert permit["reason_code"] == "REPEATED_FAILURE_FINGERPRINT"


def test_reviews_cannot_override_missing_verifier_denial_or_rejection(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    owner = auth(keys["owner_key"])
    blocked_requests: list[dict[str, Any]] = [
        {**ACTION, "required_verifier": None},
        {**ACTION, "requested_amount": "1000"},
    ]
    for body in blocked_requests:
        receipt = evaluate(client, keys["agent_key"], body).json()["receipt"]
        route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
        assert (
            client.post(
                route + "/review",
                headers=owner,
                json={"decision": "APPROVE", "reason": "Attempt override"},
            ).status_code
            == 409
        )
        assert (
            client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()[
                "allowed_now"
            ]
            is False
        )
    receipt = evaluate(client, keys["agent_key"], {**ACTION, "risk_class": "HIGH"}).json()[
        "receipt"
    ]
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
    assert (
        client.post(
            route + "/review",
            headers=owner,
            json={"decision": "REJECT", "reason": "Risk not accepted"},
        ).status_code
        == 200
    )
    assert (
        client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()["reason_code"]
        == "OWNER_REJECTED"
    )
    assert (
        client.post(
            route + "/review", headers=owner, json={"decision": "APPROVE", "reason": "Changed mind"}
        ).status_code
        == 409
    )


def test_authorization_checks_changed_policy_pause_and_expiry(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    owner = auth(keys["owner_key"])
    receipt = evaluate(client, keys["agent_key"]).json()["receipt"]
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}/authorization"
    assert client.get(route, headers=auth(keys["agent_key"])).json()["allowed_now"] is True
    config = client.get("/v1/workspace", headers=owner).json()["policy"]
    config["per_action_limit"] = "2"
    assert client.put("/v1/workspace/policy", headers=owner, json=config).status_code == 200
    assert (
        client.get(route, headers=auth(keys["agent_key"])).json()["reason_code"] == "POLICY_CHANGED"
    )
    config["agent_enabled"] = False
    assert client.put("/v1/workspace/policy", headers=owner, json=config).status_code == 200
    assert client.get(route, headers=auth(keys["agent_key"])).status_code == 403
    config["agent_enabled"] = True
    assert client.put("/v1/workspace/policy", headers=owner, json=config).status_code == 200
    receipt = evaluate(client, keys["agent_key"], {**ACTION, "risk_class": "HIGH"}).json()[
        "receipt"
    ]
    workspace_id = keys["workspace"]["id"]
    with SibylMemoryStore(tmp_path / "workspaces" / f"{workspace_id}.db", workspace_id) as memory:
        stored = memory.get_decision(receipt["receipt_id"])
        assert stored
        memory.write_decision(
            stored.model_copy(update={"expires_at": utc_now() - timedelta(seconds=1)})
        )
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
    assert (
        client.post(
            route + "/review", headers=owner, json={"decision": "APPROVE", "reason": "Too late"}
        ).status_code
        == 410
    )
    assert (
        client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()["reason_code"]
        == "RECEIPT_EXPIRED"
    )


def test_receipt_revocation_is_durable_scoped_and_keeps_other_requests_active(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys, other = create(client), create(client, "Other")
    identifier = str(uuid4())
    receipt = evaluate(client, keys["agent_key"], idempotency=identifier).json()["receipt"]
    unaffected = evaluate(client, keys["agent_key"]).json()["receipt"]
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
    body = {"reason": "The owner canceled this specific job."}
    assert client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()[
        "allowed_now"
    ]
    assert (
        client.post(route + "/revoke", headers=auth(keys["agent_key"]), json=body).status_code
        == 403
    )
    assert (
        client.post(route + "/revoke", headers=auth(other["owner_key"]), json=body).status_code
        == 404
    )
    assert (
        client.post(
            route + "/revoke", headers=auth(keys["owner_key"]), json={"reason": "  "}
        ).status_code
        == 422
    )
    saved = client.post(route + "/revoke", headers=auth(keys["owner_key"]), json=body)
    assert saved.status_code == 200
    again = client.post(route + "/revoke", headers=auth(keys["owner_key"]), json=body).json()
    assert again["idempotent_replay"] is True
    assert again["revocation"] == saved.json()["revocation"]
    assert (
        client.post(
            route + "/revoke", headers=auth(keys["owner_key"]), json={"reason": "Changed"}
        ).status_code
        == 409
    )
    restarted = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    checked = restarted.get(route + "/authorization", headers=auth(keys["agent_key"])).json()
    assert checked["allowed_now"] is False
    assert checked["reason_code"] == "RECEIPT_REVOKED"
    assert checked["revocation"]["reason"] == body["reason"]
    replay = evaluate(restarted, keys["agent_key"], idempotency=identifier).json()
    assert replay["receipt"] == receipt  # Replay remains historical, not a fresh permission check.
    untouched = restarted.get(
        f"/v1/workspace/decisions/{unaffected['receipt_id']}/authorization",
        headers=auth(keys["agent_key"]),
    ).json()
    assert untouched["allowed_now"] is True
    history = restarted.get("/v1/workspace/decisions", headers=auth(keys["owner_key"])).json()
    entry = next(item for item in history if item["receipt"]["receipt_id"] == receipt["receipt_id"])
    assert entry["receipt"]["decision"] == "APPROVE"
    assert entry["revocation"] == saved.json()["revocation"]


def test_revocation_blocks_review_approval_and_survives_policy_resume(tmp_path: Path) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    owner = auth(keys["owner_key"])
    review = {"decision": "APPROVE", "reason": "Accepted the risk."}
    for already_reviewed in (False, True):
        receipt = evaluate(client, keys["agent_key"], {**ACTION, "risk_class": "HIGH"}).json()[
            "receipt"
        ]
        route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
        if already_reviewed:
            assert client.post(route + "/review", headers=owner, json=review).status_code == 200
        assert (
            client.post(
                route + "/revoke", headers=owner, json={"reason": "Cancel this action"}
            ).status_code
            == 200
        )
        assert client.post(route + "/review", headers=owner, json=review).status_code == 409
        policy = client.get("/v1/workspace", headers=owner).json()["policy"]
        for enabled in (False, True):
            policy["agent_enabled"] = enabled
            assert client.put("/v1/workspace/policy", headers=owner, json=policy).status_code == 200
        checked = client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()
        assert checked["allowed_now"] is False
        assert checked["reason_code"] == "RECEIPT_REVOKED"


def test_revocation_read_failure_never_returns_permission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    receipt = evaluate(client, keys["agent_key"]).json()["receipt"]

    def fail_read(*args: Any, **kwargs: Any) -> Any:
        raise MemorySubsystemError("Revocation storage unavailable")

    monkeypatch.setattr(SibylMemoryStore, "get_workspace_revocation", fail_read)
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}/authorization"
    assert client.get(route, headers=auth(keys["agent_key"])).status_code == 503


def test_review_audit_failure_never_becomes_a_permit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(create_app(memory_db=tmp_path / "demo.db"))
    keys = create(client)
    receipt = evaluate(client, keys["agent_key"], {**ACTION, "risk_class": "HIGH"}).json()[
        "receipt"
    ]
    workspace_id = keys["workspace"]["id"]
    with SibylMemoryStore(tmp_path / "workspaces" / f"{workspace_id}.db", workspace_id) as memory:
        client_type = type(memory._client)

    def fail_audit(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(client_type, "write_event", fail_audit)
    route = f"/v1/workspace/decisions/{receipt['receipt_id']}"
    assert (
        client.post(
            route + "/review",
            headers=auth(keys["owner_key"]),
            json={"decision": "APPROVE", "reason": "Reviewed."},
        ).status_code
        == 503
    )
    assert (
        client.get(route + "/authorization", headers=auth(keys["agent_key"])).json()["allowed_now"]
        is False
    )
