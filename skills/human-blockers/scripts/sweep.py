"""Emit candidate human-gate lines from memory files, LAUNCH.md files and BLOCKERS.md.

Deterministic collection only. Judging whether a candidate is a real open human
gate is the skill's job, not this script's.
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("sweep")

HOME = Path.home()
MEMORY_DIR = HOME / ".claude" / "projects" / "C--Users-skf-s" / "memory"
BLOCKERS = HOME / ".claude" / "BLOCKERS.md"

# Measured against the 225 memory files on 2026-09-06; see the skill's Sources section.
# BLOCKERS.md states openness structurally, so no keyword of its own appears on a row.
UNCHECKED = re.compile(r"^- \[ \]")
OPEN_MARKERS = re.compile(
    r"blocked on|BLOCKED|NOT yet|not yet run|unset|pending|awaiting|"
    r"\bopen:|\bopen,|ASK-FIRST|REVOKE|rotate|only Keith|KEITH NEXT|"
    r"(needs?|need|waiting on|down to|up to) (Keith|his|your)|Keith (needs|must|has to)",
    re.IGNORECASE,
)
CLOSED_MARKERS = re.compile(
    r"SHIPPED|\bDONE\b|\bmet \d|CLOSED|RESOLVED|LIVE\b|PUBLISHED|SUBMITTED", re.IGNORECASE
)
MAX_LINE = 400


@dataclass(frozen=True)
class Candidate:
    path: Path
    line_no: int
    text: str

    def render(self, root: Path) -> str:
        try:
            where = self.path.relative_to(root)
        except ValueError:
            where = self.path
        return f"{where}:{self.line_no}: {self.text[:MAX_LINE]}"


def scan(path: Path) -> list[Candidate]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        log.warning("skip %s: %s", path, exc)
        return []
    hits = []
    for i, raw in enumerate(lines, 1):
        text = raw.strip()
        box_open = UNCHECKED.match(text) is not None
        if not text or not (box_open or OPEN_MARKERS.search(text)):
            continue
        # A row's own box outranks a word like "closed" or "live" in its prose.
        if not box_open and CLOSED_MARKERS.search(text):
            continue
        hits.append(Candidate(path, i, text))
    return hits


def sources(extra_roots: list[Path]) -> list[Path]:
    found = sorted(MEMORY_DIR.glob("*.md"))
    if BLOCKERS.exists():
        found.append(BLOCKERS)
    for root in extra_roots:
        found.extend(sorted(root.glob("*/docs/LAUNCH.md")))
    return found


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, action="append", default=[], help="repo parent to scan for docs/LAUNCH.md"
    )
    args = parser.parse_args()
    roots = args.root or [HOME]

    files = sources(roots)
    candidates = [c for f in files for c in scan(f)]
    for c in candidates:
        print(c.render(HOME))
    log.info("%d candidates from %d files", len(candidates), len(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
