"""Every SKILL.md front matter must parse as YAML with a string description.

A stray ": " in a plain description makes the YAML invalid, and the skill then loads with a fallback
description that never matches the user's words (improve-codebase-architecture and ugc-factory, 2026-09-24).
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
SKILLS = Path(__file__).resolve().parents[2] / "skills"
FILES = sorted(p for p in SKILLS.glob("*/SKILL.md") if not p.parent.name.endswith("-workspace"))


def test_skills_found() -> None:
    assert FILES, f"no SKILL.md under {SKILLS}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.relative_to(SKILLS).parent.as_posix())
def test_front_matter_parses_with_a_description(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        pytest.skip("no front matter")
    meta = yaml.safe_load(text.split("---", 2)[1])
    assert isinstance(meta, dict), "front matter is not a mapping"
    assert isinstance(meta.get("description"), str) and meta["description"].strip(), "no description string"
