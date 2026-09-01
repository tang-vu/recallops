from __future__ import annotations

from pathlib import Path

import pytest
from recallops.demo.reset import validated_demo_database


def test_reset_accepts_only_exact_project_demo_database(tmp_path: Path) -> None:
    expected = (tmp_path / ".data" / "demo" / "recallops-demo.db").resolve()

    assert validated_demo_database(tmp_path, str(expected)) == expected


@pytest.mark.parametrize(
    "relative_target",
    [
        "recallops-demo.db",
        ".data/recallops-demo.db",
        ".data/demo/another.db",
        ".data/demo/nested/recallops-demo.db",
        "../recallops-demo.db",
    ],
)
def test_reset_rejects_paths_outside_exact_target(tmp_path: Path, relative_target: str) -> None:
    target = (tmp_path / relative_target).resolve()

    with pytest.raises(ValueError, match="Refusing reset"):
        validated_demo_database(tmp_path, str(target))
