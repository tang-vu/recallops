"""Prove that disabling Sibyl stops production commerce and exposes stateless repeats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from recallops.benchmark.runner import SCENARIOS, _action, _stable_uuid, _stateless_outcome
from recallops.memory.port import MemoryPort, MemorySubsystemError
from recallops.models import Decision
from recallops.orchestration.guard import CommerceGuard


class DisabledMemory:
    """Deliberately unavailable dependency, not a production store implementation."""

    def load_evaluation_context(self, **_kwargs: str) -> None:
        raise MemorySubsystemError("Sibyl Memory is deliberately disabled for the deletion test")


def run_deletion_test() -> dict[str, Any]:
    spec = SCENARIOS[2]
    session_id = _stable_uuid("deletion-test-session")
    action = _action(spec.scenario_id, "deletion-test", session_id)
    stopped_receipt, writes = CommerceGuard(cast(MemoryPort, DisabledMemory())).evaluate(action)
    baseline = _stateless_outcome(spec)
    passed = (
        stopped_receipt.decision is Decision.ESCALATE
        and stopped_receipt.reason_codes == ("MEMORY_READ_FAILED",)
        and writes == []
        and baseline["decision"] == Decision.APPROVE.value
    )
    return {
        "test": "recallops-sibyl-deletion-test-v1",
        "passed": passed,
        "production_without_sibyl": {
            "decision": stopped_receipt.decision.value,
            "reason_codes": list(stopped_receipt.reason_codes),
            "commerce_stopped": True,
            "writes": writes,
        },
        "explicit_stateless_comparison": {
            "decision": baseline["decision"],
            "reason_codes": baseline["reason_codes"],
            "unsafe_repeat": baseline["decision"] == Decision.APPROVE.value,
            "production_selectable": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="benchmark/results/deletion-test.json")
    args = parser.parse_args()
    report = run_deletion_test()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
