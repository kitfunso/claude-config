#!/usr/bin/env python3
"""PreToolUse hook (Write): backstop for the Hand-Maintained Files rule in CLAUDE.md.

Denies a Write over an existing CLAUDE.md anywhere, over ~/.claude/settings.json (per box,
so git never tracks it), or over an existing file that git tracks in ~/.claude, unless the
latest human prompt holds the word "apply". New and other untracked files pass, and Edit
never reaches this hook. When ~/.claude is not a git checkout, git fails and every file
there reads as untracked.
Escape hatch: CLAUDE_REWRITE_GATE=off. On any error the Write is allowed, one stderr line
names the error and the hook exits 0; a broken guard must not break the session.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
try:
    from record_component import record
except Exception:  # the recorder is optional, the deny is not
    def record(**_: object) -> None:
        return None

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
APPLY = re.compile(r"\bapply\b", re.I)
REASON = (
    "[REWRITE GATE] {path} is hand-maintained and this Write replaces all of it. Per the "
    "Hand-Maintained Files rule in CLAUDE.md: show Keith the proposed content and wait for an "
    "explicit \"apply\", or make the change with targeted Edits. "
    "Escape hatch: CLAUDE_REWRITE_GATE=off."
)


def tracked(target: Path) -> bool:
    """Only git knows; a path outside ~/.claude, or a failing git, reads as untracked."""
    try:
        rel = target.relative_to(CLAUDE_DIR.resolve())
    except ValueError:
        return False
    out = subprocess.run(
        ["git", "-C", str(CLAUDE_DIR), "ls-files", "--error-unmatch", "--", rel.as_posix()],
        capture_output=True, timeout=5,
    )
    return out.returncode == 0


def approved(transcript: str) -> bool:
    # Imported late: most Writes never need the transcript.
    from reply_check import last_prompt
    return bool(APPLY.search(last_prompt(Path(transcript))))


def decide(payload: dict) -> dict | None:
    """The deny output for a gated Write, else None."""
    if payload.get("tool_name") != "Write":
        return None
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path or not Path(file_path).is_file():
        return None
    target = Path(file_path).resolve()
    gated = target.name.lower() == "claude.md" or target == (CLAUDE_DIR / "settings.json").resolve()
    if not gated and not tracked(target):
        return None
    if approved(str(payload.get("transcript_path") or "")):
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": REASON.format(path=target)}}


def main() -> None:
    if os.environ.get("CLAUDE_REWRITE_GATE", "").lower() == "off":
        return
    payload = json.loads(sys.stdin.buffer.read())
    out = decide(payload)
    if out:
        record(kind="hook", name=Path(__file__).name, session_id=payload.get("session_id"),
               cwd=payload.get("cwd"), blocked=True,
               notes=out["hookSpecificOutput"]["permissionDecisionReason"])
        json.dump(out, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - a guard must never break the session
        print(f"rewrite_gate: {type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(0)
