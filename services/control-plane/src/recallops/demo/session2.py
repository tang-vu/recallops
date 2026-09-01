"""Session 2: recall Agent A's failure in a fresh process and choose Agent B."""

from __future__ import annotations

import argparse
import json

from recallops.demo.common import (
    DEMO_TENANT,
    action,
    process_metadata,
    resolve_database,
    session_id,
)
from recallops.memory.sibyl_store import SibylMemoryStore
from recallops.models import Decision
from recallops.orchestration.guard import CommerceGuard


def run(database: str, tenant_id: str = DEMO_TENANT) -> dict[str, object]:
    current_session = session_id()
    metadata = process_metadata(current_session)
    with SibylMemoryStore(resolve_database(database), tenant_id) as memory:
        memory.set_active_session(
            str(current_session),
            {
                "process_id": str(metadata["process_id"]),
                "utc_timestamp": str(metadata["utc_timestamp"]),
                "git_commit": str(metadata["git_commit"]),
                "demo_stage": "SESSION_2",
            },
        )
        guard = CommerceGuard(memory)
        agent_a_receipt, agent_a_writes = guard.evaluate(action("agent-a", current_session))
        agent_b_receipt, agent_b_writes = guard.evaluate(action("agent-b", current_session))
        health = memory.health()

    failure_evidence = [
        item.model_dump(mode="json")
        for item in agent_a_receipt.memory_evidence
        if item.record_type == "failure_fingerprint"
    ]
    return {
        "demo_stage": "SESSION_2",
        "integration_mode": "REAL SIBYL LOCAL",
        "process": metadata,
        "selection_attempt": {
            "initial_preference": "Agent A",
            "why": "Agent A costs 1.00 USDC; Agent B costs 1.50 USDC.",
        },
        "retrieved_memory_record": failure_evidence,
        "agent_a_decision": agent_a_receipt.model_dump(mode="json"),
        "agent_b_decision": agent_b_receipt.model_dump(mode="json"),
        "selected_provider": "Agent B" if agent_b_receipt.decision == Decision.APPROVE else None,
        "execution": {
            "status": "NOT_EXECUTED",
            "reason": "Virtuals fixture and live adapters are introduced in Milestone 4.",
            "virtuals_job_id": None,
            "base_transaction_hash": None,
        },
        "new_sibyl_writes": agent_a_writes + agent_b_writes,
        "sibyl_health": health,
        "process_terminated_after_output": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Same durable Sibyl database used by Session 1")
    parser.add_argument("--tenant", default=DEMO_TENANT)
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.tenant), indent=2, default=str))


if __name__ == "__main__":
    main()
