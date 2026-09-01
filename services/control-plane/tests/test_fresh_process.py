from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


def run_module(module: str, database: Path) -> dict[str, Any]:
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", module, "--db", str(database)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return cast(dict[str, Any], json.loads(completed.stdout))


def test_fresh_process_recall_changes_economic_decision(tmp_path: Path) -> None:
    database = (tmp_path / "fresh-process.db").resolve()

    first = run_module("recallops.demo.session1", database)
    second = run_module("recallops.demo.session2", database)

    assert first["process"]["process_id"] != second["process"]["process_id"]
    assert first["process"]["session_id"] != second["process"]["session_id"]
    assert first["verification"]["outcome"] == "REJECTED"
    assert second["agent_a_decision"]["decision"] == "DENY"
    assert "REPEATED_FAILURE_FINGERPRINT" in second["agent_a_decision"]["reason_codes"]
    assert second["retrieved_memory_record"]
    assert second["agent_b_decision"]["decision"] == "APPROVE"
    assert second["selected_provider"] == "Agent B"
