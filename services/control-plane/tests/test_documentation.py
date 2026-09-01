from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_DOCUMENTS = (
    "docs/judging-map.md",
    "docs/demo-script.md",
    "docs/submission-checklist.md",
    "docs/build-log.md",
    "docs/memory-implementation.md",
    "docs/security-model.md",
    "docs/architecture.md",
    "docs/evidence/README.md",
    "docs/research/problem-validation.md",
    "docs/research/technical-discovery.md",
)
REQUIRED_README_SECTIONS = (
    "Why it exists",
    "Product walkthrough",
    "Load-bearing memory proof",
    "Architecture",
    "Decision pipeline",
    "Memory data model",
    "Quick start",
    "Tests",
    "Benchmark results",
    "Deletion test",
    "Virtuals integration",
    "Base integration",
    "Security and privacy",
    "Known limitations",
    "Prior Work",
    "License",
    "Builder",
)
MARKDOWN_LINK = re.compile(r"!?\[[^]]*]\(([^)]+)\)")


def test_required_judging_documents_and_readme_sections_exist() -> None:
    assert all((REPOSITORY_ROOT / relative).is_file() for relative in REQUIRED_DOCUMENTS)
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    headings = set(re.findall(r"^##+\s+(.+)$", readme, flags=re.MULTILINE))
    assert set(REQUIRED_README_SECTIONS).issubset(headings)


def test_local_markdown_links_resolve() -> None:
    markdown_files = [
        REPOSITORY_ROOT / "README.md",
        *sorted((REPOSITORY_ROOT / "docs").rglob("*.md")),
    ]
    missing: list[str] = []
    for markdown in markdown_files:
        content = markdown.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = raw_target.strip().strip("<>").split("#", maxsplit=1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (markdown.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{markdown.relative_to(REPOSITORY_ROOT)} -> {raw_target}")
    assert missing == []


def test_copyable_project_documentation_avoids_long_em_dash() -> None:
    files = [
        REPOSITORY_ROOT / "README.md",
        REPOSITORY_ROOT / "STATUS.md",
        *sorted((REPOSITORY_ROOT / "docs").rglob("*.md")),
    ]
    offenders = [
        str(path.relative_to(REPOSITORY_ROOT))
        for path in files
        if "—" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
