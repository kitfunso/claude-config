#!/usr/bin/env python3
"""PreToolUse hook (Edit|Write): backstop for the Hand-Maintained Files rule.

Before Claude edits or overwrites a hand-maintained file — anything under
~/.claude (config, rules, skills, scripts, voice) or any CLAUDE.md anywhere —
save a dated `.old-YYYYMMDD` backup next to it. One backup per file per day.
The repo .gitignore already excludes `*.old*`, so backups never get committed.

Excluded: machine-managed state under ~/.claude (projects/ memory, todos,
shell-snapshots, statsig, plugins, history) and scratch dirs (*-workspace).

Contract: reads hook JSON on stdin, silent on success, always exits 0.
Never blocks an edit — a broken guard must not break the session.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
EXCLUDED_PARTS = {"projects", "todos", "shell-snapshots", "statsig", "plugins",
                  "history", "sessions", "__pycache__", "node_modules"}


def is_hand_maintained(path: Path) -> bool:
    if path.name.lower() == "claude.md":
        return True
    try:
        rel = path.resolve().relative_to(CLAUDE_DIR.resolve())
    except ValueError:
        return False
    parts = {p.lower() for p in rel.parts[:-1]}
    if parts & EXCLUDED_PARTS:
        return False
    if any(p.lower().endswith("-workspace") for p in rel.parts):
        return False
    if ".old" in path.name:
        return False
    return path.suffix.lower() in {".md", ".json", ".py"}


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path:
        return
    target = Path(file_path)
    if not target.is_file() or not is_hand_maintained(target):
        return
    backup = target.with_name(f"{target.name}.old-{date.today():%Y%m%d}")
    if backup.exists():
        return
    shutil.copy2(target, backup)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
