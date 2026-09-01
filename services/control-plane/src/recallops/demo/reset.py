"""Safely reset only the project-owned deterministic demo database."""

from __future__ import annotations

import argparse
from pathlib import Path


def validated_demo_database(repository_root: Path, raw_path: str) -> Path:
    root = repository_root.resolve()
    allowed_directory = (root / ".data" / "demo").resolve()
    target = Path(raw_path).expanduser().resolve()
    if target.parent != allowed_directory or target.name != "recallops-demo.db":
        raise ValueError(
            "Refusing reset: target must be exactly .data/demo/recallops-demo.db in this repository"
        )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "RESET_RECALLOPS_DEMO":
        raise SystemExit("Confirmation must be exactly RESET_RECALLOPS_DEMO")
    repository_root = Path(__file__).resolve().parents[5]
    target = validated_demo_database(repository_root, args.db)
    removed: list[str] = []
    for path in (target, Path(f"{target}-wal"), Path(f"{target}-shm")):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    print({"reset": str(target), "removed": removed, "recoverable": False})


if __name__ == "__main__":
    main()
