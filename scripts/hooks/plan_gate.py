#!/usr/bin/env python3
"""PreToolUse hook (ExitPlanMode): backstop for "Plans use html-plan" in CLAUDE.md.

Denies leaving plan mode until the main-thread transcript shows the html-plan skill invoked,
as a Skill tool call or a typed /html-plan. Escape hatch: CLAUDE_PLAN_GATE=off. On any error
the call is allowed and one stderr line names it; a broken guard must not break the session.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
try:
    from record_component import record
except Exception:  # the recorder is optional, the deny is not
    def record(**_: object) -> None:
        return None

TYPED = re.compile(r"<command-name>/?(?:[\w-]+:)?html-plan</command-name>")
REASON = (
    "[PLAN GATE] CLAUDE.md, Plans use html-plan: invoke the html-plan skill, write the plan as "
    "its packed HTML page, hand over the path, then call ExitPlanMode. "
    "Escape hatch: CLAUDE_PLAN_GATE=off."
)


def invoked(row: dict) -> bool:
    content = (row.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(TYPED.search(content))
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            if str((block.get("input") or {}).get("skill", "")).endswith("html-plan"):
                return True
        elif block.get("type") == "text" and TYPED.search(str(block.get("text"))):
            return True
    return False


def seen(transcript: Path) -> bool:
    with transcript.open("rb") as fh:
        for raw in fh:
            if b"html-plan" not in raw:  # byte probe: transcripts reach hundreds of MB
                continue
            try:
                row = json.loads(raw)
            except ValueError:
                continue
            if isinstance(row, dict) and not row.get("isSidechain") and invoked(row):
                return True
    return False


def decide(payload: dict) -> dict | None:
    """The deny output for an ExitPlanMode with no html-plan call behind it, else None."""
    if payload.get("tool_name") != "ExitPlanMode":
        return None
    path = payload.get("transcript_path")
    if not path or not Path(path).is_file() or seen(Path(path)):
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": REASON}}


def main() -> None:
    if os.environ.get("CLAUDE_PLAN_GATE", "").lower() == "off":
        return
    payload = json.loads(sys.stdin.buffer.read())
    out = decide(payload)
    if out:
        record(kind="hook", name=Path(__file__).name, session_id=payload.get("session_id"),
               cwd=payload.get("cwd"), blocked=True, notes=REASON)
        json.dump(out, sys.stdout)


if __name__ == "__main__":
    logging.basicConfig(format="%(name)s: %(message)s")
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - a guard must never break the session
        logging.getLogger("plan_gate").error("%s: %s", type(exc).__name__, exc)
    sys.exit(0)
