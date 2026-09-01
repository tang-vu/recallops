"""Session 1: persist a verifier-rejected Agent A outcome, then exit."""

from __future__ import annotations

import argparse
import json

from recallops.demo.common import (
    DEMO_OWNER,
    DEMO_TENANT,
    TASK_CATEGORY,
    TASK_FINGERPRINT,
    budget,
    policy,
    process_metadata,
    resolve_database,
    session_id,
)
from recallops.memory.sibyl_store import SibylMemoryStore
from recallops.models import FailureFingerprint


def run(database: str, tenant_id: str = DEMO_TENANT) -> dict[str, object]:
    current_session = session_id()
    metadata = process_metadata(current_session)
    writes: list[dict[str, str]] = []
    with SibylMemoryStore(resolve_database(database), tenant_id) as memory:
        memory.set_active_session(
            str(current_session),
            {
                "process_id": str(metadata["process_id"]),
                "utc_timestamp": str(metadata["utc_timestamp"]),
                "git_commit": str(metadata["git_commit"]),
                "demo_stage": "SESSION_1",
            },
        )
        writes.append(
            {
                "tier": "HOT",
                "record_type": "active_session",
                "record_name": "recallops:active-session",
                "sibyl_record_id": "state-key",
                "status": "written",
            }
        )
        writes.extend(memory.write_policy(policy(), str(current_session)))
        writes.extend(memory.write_budget(budget(current_session)))
        writes.extend(
            memory.write_failure(
                FailureFingerprint(
                    tenant_id=DEMO_TENANT,
                    provider_id="agent-a",
                    task_category=TASK_CATEGORY,
                    task_fingerprint=TASK_FINGERPRINT,
                    verifier_id="deterministic-schema-verifier-v1",
                    verification_reason="Required vulnerability evidence was absent.",
                    source_session_id=current_session,
                    job_reference=None,
                )
            )
        )
        health = memory.health()
    return {
        "demo_stage": "SESSION_1",
        "integration_mode": "REAL SIBYL LOCAL",
        "process": metadata,
        "owner_id": DEMO_OWNER,
        "provider": "Agent A",
        "fixture_job": "deterministic verification fixture; no fake ACP job ID",
        "verification": {
            "outcome": "REJECTED",
            "reason": "Required vulnerability evidence was absent.",
            "task_category": TASK_CATEGORY,
            "task_fingerprint": TASK_FINGERPRINT,
        },
        "sibyl_health": health,
        "successful_sibyl_writes": writes,
        "process_terminated_after_output": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", required=True, help="Absolute or resolvable Sibyl demo database path"
    )
    parser.add_argument("--tenant", default=DEMO_TENANT)
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.tenant), indent=2, default=str))


if __name__ == "__main__":
    main()
