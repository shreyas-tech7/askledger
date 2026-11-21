"""Repo quality bar: README parts in order, writing rules, ship files, study kit."""

import json
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"```.*?```", re.S)
CODE = re.compile(r"`[^`]*`")
URL = re.compile(r"https?://\S+")
SECTIONS = [
    "## The problem",
    "## How it works",
    "## Results",
    "## Cost per task",
    "## Run it in 10 minutes",
    "## Limits",
    "## Glossary",
    "## Related work",
    "## How this was built",
    "## Human checks",
]


def test_readme_parts_in_order():
    text = (ROOT / "README.md").read_text()
    pos = [text.index(s) for s in SECTIONS]
    assert text.index("**Status:**") < pos[0] and pos == sorted(pos)
    assert "```mermaid" in text and "badge.svg" in text
    assert "docs/build/BUILD_PROMPT.md" in text and "Not done yet" in text
    assert "What it does not stop" in text and "synthetic" in text


def _prose(path: Path) -> str:
    return URL.sub("", CODE.sub("", FENCE.sub("", path.read_text(encoding="utf-8"))))


DOCS = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "CHANGELOG.md"] + [
    p for p in sorted((ROOT / "docs").glob("*.md")) if p.name != "DEMO.md"
]


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_writing_rules(path):
    text = _prose(path)
    assert "—" not in text and "–" not in text, "no em or en dashes"
    assert " - " not in re.sub(r"\n\s*- ", "\n", text), "no dashes as punctuation"
    for line in text.splitlines():
        if not line.startswith("|"):
            assert ";" not in line, f"semicolon in prose: {line}"
    for bad in ("it is important to note", "testament", "pivotal", "seamless", "delve", "leverage"):
        assert bad not in text.lower()


def test_ship_files():
    for f in [
        "LICENSE",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        ".env.example",
        ".pre-commit-config.yaml",
        ".github/workflows/ci.yml",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        "docs/index.html",
        "docs/DEMO.md",
        "docs/topics.txt",
        "docs/GITHUB_ABOUT.md",
        "docs/HUMAN_STEPS.md",
        "docs/handoff/COWORK_PROMPT.md",
        "docs/build/BUILD_PROMPT.md",
        "docs/TOOLING.md",
        "DECISIONS.md",
    ]:
        assert (ROOT / f).is_file(), f
    assert "Copyright (c) 2026 Shreyas" in (ROOT / "LICENSE").read_text()


def test_study_kit():
    walk = (ROOT / "docs" / "WALKTHROUGH.md").read_text()
    qa = (ROOT / "docs" / "INTERVIEW_QA.md").read_text()
    assert len(re.findall(r"^\*\*\d+\.", qa, re.M)) >= 15
    # every function the study kit names must exist
    src = "\n".join(p.read_text() for p in (ROOT / "src" / "askledger").glob("*.py"))
    for name in set(re.findall(r"`(?:\w+\.)?(_?[a-z]\w+)\(\)`", walk)):
        assert re.search(rf"def {name}\b", src), name
    for name in set(re.findall(r"`\w+\.(_?[a-z_]\w+)`", qa)) - {"py", "md", "json", "jsonl"}:
        assert re.search(rf"def {name}\b", src), name
    for topic in ("execution accuracy", "below the model", "set_authorizer", "repair"):
        assert topic in qa.lower() or topic in qa


def test_static_page_opens_from_disk():
    page = (ROOT / "docs" / "index.html").read_text()
    assert "<table>" in page and "<script" not in page and "http" not in page.split("<body>")[1]


def test_social_preview_size():
    head = (ROOT / "docs" / "social-preview.png").read_bytes()[:24]
    assert struct.unpack(">II", head[16:24]) == (1280, 640)


def test_topics():
    topics = (ROOT / "docs" / "topics.txt").read_text().split()
    assert 5 <= len(topics) <= 20
    assert all(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,24}", t) for t in topics)


def test_feature_flags_are_honest():
    features = json.loads((ROOT / "feature_list.json").read_text())
    blocked = (ROOT / "BLOCKERS.md").read_text()
    for f in features:
        if not f["passes"]:
            assert f["id"] in blocked, f"{f['id']} is false but not in BLOCKERS.md"


def test_link_check_passes():
    r = subprocess.run(  # noqa: S603 (fixed argv, our own script)
        [sys.executable, str(ROOT / "scripts" / "check_links.py")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stdout
