#!/usr/bin/env python3
"""UserPromptSubmit hook: backstop for the Do It Properly rule in ~/.claude/CLAUDE.md.

Injects the staged-work rule into context on every prompt, the same shape as human_voice.py,
because a rule in memory alone lost to the pull to declare research finished (2026-09-22).
A bare go or continue (time_ledger's approval-only prompt) adds the keep-going sentence.
Escape hatch: CLAUDE_DO_IT_PROPERLY=off. Always exits 0; a broken guard must not break the session.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from time_ledger import APPROVAL
except Exception as exc:  # noqa: BLE001 - the keep-going sentence is optional, the rule is not
    logging.getLogger("do_it_properly").warning("no bare-go check: %s: %s", type(exc).__name__, exc)
    APPROVAL = re.compile(r"(?!)")

BARE_GO = (
    "[KEEP GOING] Keith had to send a bare go, so the last turn stopped before his goal was done. "
    "Run the whole remaining plan to the end in this turn; a stage boundary is a log line, not a stop. "
    "Stop only for an ASK-FIRST item, a failed check or a real blocker, named in one line. "
    "If his prompt asks a question, answer it instead."
)
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


def context(raw: str) -> str:
    """The rule, plus the keep-going sentence when the prompt is a bare go."""
    try:
        prompt = str(json.loads(raw).get("prompt") or "").strip()
    except (ValueError, AttributeError):
        prompt = ""
    return f"{RULE}\n{BARE_GO}" if len(prompt) <= 60 and APPROVAL.match(prompt) else RULE


def main() -> int:
    if os.environ.get("CLAUDE_DO_IT_PROPERLY", "").lower() == "off":
        return 0
    json.dump(
        {
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context(sys.stdin.read())},
            "suppressOutput": True,
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(format="%(name)s: %(message)s")
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a guard must never break the session
        logging.getLogger("do_it_properly").error("%s: %s", type(exc).__name__, exc)
        sys.exit(0)
