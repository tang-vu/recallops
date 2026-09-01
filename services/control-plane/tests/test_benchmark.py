from __future__ import annotations

import csv
import json
from pathlib import Path

from recallops.benchmark.deletion import run_deletion_test
from recallops.benchmark.runner import BENCHMARK_SEED, run_benchmark, write_artifacts


def test_twelve_scenarios_compare_real_sibyl_with_stateless_baseline(tmp_path: Path) -> None:
    report = run_benchmark(tmp_path / "benchmark.db", seed=BENCHMARK_SEED)

    assert report["scenario_count"] == 12
    assert len(report["results"]) == 24
    assert report["summary"]["sibyl_memory"]["decision_accuracy_percent"] == 100.0
    assert report["summary"]["sibyl_memory"]["unsafe_repeat_rate_percent"] == 0.0
    assert report["summary"]["stateless_baseline"]["unsafe_repeat_rate_percent"] == 100.0
    assert report["summary"]["stateless_baseline"]["budget_violation_rate_percent"] == 50.0
    assert "never selectable in production" in report["mode_disclosure"]["STATELESS_BASELINE"]


def test_benchmark_exports_json_csv_and_markdown(tmp_path: Path) -> None:
    report = run_benchmark(tmp_path / "export.db")
    output = tmp_path / "results"
    write_artifacts(report, output)

    parsed = json.loads((output / "latest.json").read_text(encoding="utf-8"))
    with (output / "latest.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    markdown = (output / "latest.md").read_text(encoding="utf-8")

    assert parsed["run_id"] == report["run_id"]
    assert len(rows) == 24
    assert "| 12 | Missing owner policy memory | ESCALATE | ESCALATE | APPROVE |" in markdown


def test_deletion_test_stops_production_and_exposes_unsafe_baseline() -> None:
    result = run_deletion_test()

    assert result["passed"] is True
    assert result["production_without_sibyl"]["decision"] == "ESCALATE"
    assert result["explicit_stateless_comparison"]["decision"] == "APPROVE"
    assert result["explicit_stateless_comparison"]["production_selectable"] is False
