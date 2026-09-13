#!/usr/bin/env python3
"""Measure the per-prompt context tax of Keith-controlled text, in cl100k_base tokens.

Skill and agent listings are rebuilt from frontmatter as "- /name: description" lines,
so they approximate what Claude Code injects: deltas are exact, levels are close.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import tiktoken

HOME = Path("C:/Users/skf_s")
CLAUDE_DIR = HOME / ".claude"
ENC = tiktoken.get_encoding("cl100k_base")


@dataclass(frozen=True)
class Row:
    name: str
    tokens: int
    note: str


def tokens(text: str) -> int:
    return len(ENC.encode(text, disallowed_special=()))


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out: dict[str, str] = {}
    key = ""
    for line in text[3:end].splitlines():
        match = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if match and not line.startswith(" "):
            key = match.group(1)
            value = match.group(2).strip()
            out[key] = "" if value in (">", "|", ">-", "|-") else value.strip("'\"")
        elif key and line.startswith(" "):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def listing(paths: list[Path]) -> tuple[str, int]:
    lines: list[str] = []
    for path in paths:
        meta = frontmatter(path)
        if meta.get("disable-model-invocation", "").lower() == "true":
            continue
        name = meta.get("name") or path.parent.name
        lines.append(f"- /{name}: {meta.get('description', '')}")
    return "\n".join(lines), len(lines)


def hippo_payload(cwd: str) -> tuple[str, str]:
    digest = hashlib.sha1(cwd.encode("utf-8")).hexdigest()[:16]
    cache = CLAUDE_DIR / "cache" / "hippo-context" / f"{digest}.json"
    if not cache.exists():
        return "", f"no cache for {cwd}"
    raw = cache.read_text(encoding="utf-8")
    try:
        return json.loads(raw)["hookSpecificOutput"]["additionalContext"], cache.name
    except (ValueError, KeyError, TypeError):
        return raw, cache.name


def hippo_rows(text: str, note: str) -> tuple[Row, Row]:
    cut = text.find("## Project Memory")
    snapshot, memory = (text[:cut], text[cut:]) if cut > 0 else ("", text)
    header = re.search(r"## Project Memory \((\d+) entries, (\d+) tokens\)", text)
    own = f"hippo counts {header.group(2)} for {header.group(1)} entries" if header else note
    return (
        Row("hippo memory block", tokens(memory), own),
        Row("hippo task snapshot", tokens(snapshot), "Active Task Snapshot" if snapshot else "none"),
    )


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    skills_text, n_skills = listing(sorted(CLAUDE_DIR.glob("skills/*/SKILL.md")))
    agents_text, n_agents = listing(sorted(CLAUDE_DIR.glob("agents/*.md")))
    rules = sorted(CLAUDE_DIR.glob("rules/*.md"))
    cwd = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/skf_s"
    hippo_text, hippo_note = hippo_payload(cwd)
    memory_index = CLAUDE_DIR / "projects/C--Users-skf-s/memory/MEMORY.md"
    rows = (
        Row("skill listing", tokens(skills_text), f"{n_skills} skills"),
        Row("global CLAUDE.md", tokens(read(CLAUDE_DIR / "CLAUDE.md")), ""),
        Row("MEMORY.md", tokens(read(memory_index)), ""),
        Row("agent listing", tokens(agents_text), f"{n_agents} agents"),
        *hippo_rows(hippo_text, hippo_note),
        Row("rules/*.md", sum(tokens(read(p)) for p in rules), f"{len(rules)} files"),
        Row("~/CLAUDE.md", tokens(read(HOME / "CLAUDE.md")), ""),
    )
    print(f"cl100k_base tokens per prompt; hippo cache for cwd {cwd}")
    width = max(len(row.name) for row in rows)
    for row in rows:
        print(f"{row.name:<{width}}  {row.tokens:>6,}  {row.note}")
    print(f"{'total':<{width}}  {sum(row.tokens for row in rows):>6,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
