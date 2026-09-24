#!/usr/bin/env python3
"""UserPromptSubmit hook: backstop for the Do It Properly rule in ~/.claude/CLAUDE.md.

Injects the staged-work rule into context on every prompt, the same shape as human_voice.py,
because a rule in memory alone lost to the pull to declare research finished (2026-09-22).
Escape hatch: CLAUDE_DO_IT_PROPERLY=off. Always exits 0; a broken guard must not break the session.
"""

from __future__ import annotations

import json
import os
import sys

RULE = (
    "[DO IT PROPERLY] Keith's standing rule: no rushing when building anything, a model most of "
    "all. Work in named stages, each closed by its own check; before calling anything finished, "
    "report every stage as done, partial or skipped. Never claim 'tried everything' or 'every "
    "table' without the list of what was and was not covered. Read a reference in full before "
    "summarising it; search a whole table family before calling data absent. A daily read with a "
    "ledger is the last stage of research, never 'shipping'. Never skip a check to save time. A "
    "pause between stages is not a check: approved work runs straight through, and the stage "
    "report goes in the final message."
)


def main() -> int:
    if os.environ.get("CLAUDE_DO_IT_PROPERLY", "").lower() == "off":
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
