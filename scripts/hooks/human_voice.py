#!/usr/bin/env python3
"""UserPromptSubmit hook: backstop for the Human Voice rule in ~/.claude/CLAUDE.md.

Injects the reply-shape rule into context on every prompt, so it sits in the freshest
context instead of a 4k-token rules file where it lost every conflict. Escape hatch:
CLAUDE_HUMAN_VOICE=off. Always exits 0; a broken guard must not break the session.
"""

from __future__ import annotations

import json
import os
import sys

RULE = (
    "[HUMAN VOICE] Keith's standing rule, outranks the pull to cite everything: reply like a "
    "person talking across a desk. First sentence is the answer. Default under 8 lines; go "
    "long only when asked or when the task truly needs it. Two or three numbers at most, the "
    "ones that carry the point; the rest live on the page or in the file. No tables and no "
    "bullet walls in chat. Plain words; explain a term of art right after using it. Sourcing "
    "says where a number comes from, never how many to list."
)


def main() -> int:
    if os.environ.get("CLAUDE_HUMAN_VOICE", "").lower() == "off":
        return 0
    sys.stdin.read()
    json.dump(
        {
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": RULE},
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
