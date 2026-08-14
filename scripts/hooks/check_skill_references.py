#!/usr/bin/env python3
"""UserPromptSubmit hook: backstop for the Capability Existence Check rule.

Scans the submitted prompt for /slash-command style references and, for any that
match a skill or command actually installed on disk, injects a [CAPABILITY EXISTS]
notice into the model's context. This makes "that skill doesn't exist" a harder
mistake to make.

Contract: reads hook JSON on stdin, writes hook JSON on stdout, always exits 0.
Never blocks a prompt - a broken guard must not break the session.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"

# A slash reference at a word boundary: /skill-name, not a/path/fragment.
SLASH_REF = re.compile(r"(?:^|[\s(\[`\"'])/([a-zA-Z][a-zA-Z0-9_-]{1,63})")


def installed_capabilities() -> dict[str, str]:
    """Map capability name -> where it lives. Directory names are authoritative."""
    found: dict[str, str] = {}

    for root in (CLAUDE_DIR / "skills", CLAUDE_DIR / "plugins"):
        if not root.is_dir():
            continue
        for skill_md in root.rglob("SKILL.md"):
            found.setdefault(skill_md.parent.name, str(skill_md.parent))

    commands = CLAUDE_DIR / "commands"
    if commands.is_dir():
        for cmd in commands.rglob("*.md"):
            found.setdefault(cmd.stem, str(cmd))

    return found


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except (ValueError, TypeError):
        payload = {}

    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        prompt = raw  # fall back to scanning the whole payload

    referenced = {m.group(1) for m in SLASH_REF.finditer(prompt)}
    if not referenced:
        return 0

    installed = installed_capabilities()
    hits = sorted(name for name in referenced if name in installed)
    if not hits:
        return 0

    lines = [f"  /{name}  ->  {installed[name]}" for name in hits]
    context = (
        "[CAPABILITY EXISTS] The prompt references capabilities that ARE "
        "installed on disk. Do not tell the user they don't exist, and do not "
        "substitute a different approach without saying so first:\n"
        + "\n".join(lines)
    )

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            },
            "suppressOutput": True,
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a guard must never break the session
        sys.exit(0)
