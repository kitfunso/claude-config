#!/usr/bin/env python3
"""Stop hook: backstop for the Decisiveness rule in ~/.claude/CLAUDE.md ("a go covers the whole plan").

When the last sentences of a reply ask for a go ("say go", "shall I", "want me to", "next is X",
a bare "Go?") or wait for a schedule, the stop is blocked once and Claude carries on. It passes when
that sentence or the next names an ASK-FIRST reason (deploy, push, delete, cost, an outside service,
sign-off), waits on Keith's hands, or offers a choice between named options; and when his prompt
was a question, or a turn of a skill whose contract is to wait for him (all-done, grill-me).
The second stop always passes (stop_hook_active), so a block cannot loop. Each block is logged to
~/.claude/state/keep_going.jsonl. Escape hatch: CLAUDE_KEEP_GOING=off. Always exits 0.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from reply_check import last_prompt, prose

LOG = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "state" / "keep_going.jsonl"
TAIL_LINES = 2
ASK = re.compile("|".join((
    r"(?<!\bI )\b(?:say|reply|type)\s+[*\"“'`]*(?:go|yes|apply)\b|\bsay (?:the word|so)\b",
    r"[\"“*]+(?:go|yes|apply(?: consolidated)?)[\"”*]+\s+(?:makes|starts|runs|applies|kicks)\b",
    r"\b(?:want|would you like|do you want) me to\b",
    r"\b(?:shall|should) I\b",
    r"\bif you(?:'d| would)? (?:want|like|prefer)\b(?=[^.?!]*\b(?:I|me)\b)",
    r"\b(?:I|me)\b[^.?!]*\bif you(?:'d| would)? (?:want|like|prefer)\b",
    r"\blet me know (?:if|whether|when|which)\b",
    r"\bwhenever you(?:'re ready| want| like)\b",
    r"\b(?:tell me|when you say)\b[^.?!]{0,60}\bI(?:'ll| will)\b",
    r"\bnext (?:is|up|step)\b|\bnext\b\W{0,2}:|\bcomes next\b|^\W*(?:then|after that),? I(?:'ll| will)\b",
    r"\bneeds? (?:your|a|its own) (?:second |own )?(?:go|yes|ok)\b|\bwait(?:s|ing)? (?:on|for) your (?:go|yes)\b",
    r"\bnext scheduled\b|\b(?:until|about|around) \d{1,2}:\d{2}\b",
    r"(?:^|\s)(?:go|proceed|ok(?:ay)?|shall we)\?\W*$",
)), re.I)
ASK_FIRST = re.compile(
    r"\b(?:deploy|promot|delet|overwrit|migrat|irreversib|destructiv|publish|credential|complian|approval|ruling)"
    r"|\b(?:push(?:ed|ing)?|force|schema|prod|production|live data|costs?(?! nothing)|paid|spend|money|billing|outside|external|"
    r"third[- ]party|send|email|sign(?:ed)?[- ]?off|fork|taste|your call|password|secret|only you|yourself|"
    r"needs? you to|new conversation|restart|sudo|log ?in|permission mode)\b|\$\d", re.I)
HANDS = re.compile(
    r"\b(?:once|when|after) (?:it|that|this|you|the (?!next)\w+)\b[^.?!]{0,40}\b(?:done|run|ran|finished|finishes|"
    r"exits|lands|completes|pasted|switched|installed|on)\b|\bonce pasted\b"
    r"|\btell me (?:when )?(?:it's|it is|it has|you've|you have)\b", re.I)
CHOICE = re.compile(
    r"\b(?:go )?(?:\d|[A-D])\b[\"”'`*]*\s+or\s+[\"“'`*]*(?:go )?(?:\d|[A-D]|both)\b|\bwhich (?:one|option)\b"
    r"|\b(?:should I|shall I|want me to)\b[^?]*,\s+or\s+[^?]*\?|\bshortlist\b|\byou meant\b", re.I)
QUESTION = re.compile(r"^(?:\S+\s+){2,}\S*\?\s*$|^(?:what|why|how|is|are|can|could|does|do|did|where|which|who|"
                      r"explain|describe|tell me|rate|compare)\b(?:\s+\S+){2,}", re.I | re.S)
WAITING_SKILL = re.compile(r"<command-name>/?(?:all-done|grill-me)\b")
SENTENCE = re.compile(r"(?<=[.!?])\s+")
REASON = ("keep_going: your reply stops on {hit!r}, handing the next step back to Keith or waiting on a schedule. "
          "His rule: a go covers the whole plan, and jobs get driven instead of waited for, so never end on "
          "'Next is X', 'Say go' or 'Should I'. If that step is inside what he asked for, do it now. If it is on the "
          "ASK-FIRST list or needs his hands (deploy, cost, destructive, a genuine fork), say which in one line and "
          "stop. Don't repeat the question.")


def asking(reply: str) -> str:
    """The first go-seeking phrase in the reply's last lines with no reason to stop in its sentence or the next."""
    sentences = SENTENCE.split(" ".join(prose(reply)[-TAIL_LINES:]))
    for i, sentence in enumerate(sentences):
        hit = ASK.search(sentence)
        near = " ".join(sentences[i:i + 2])
        if hit and not (ASK_FIRST.search(near) or HANDS.search(near) or CHOICE.search(near)):
            return hit.group(0).strip()
    return ""


def verdict(payload: dict, prompt: str) -> str:
    """The go-seeking phrase that blocks this stop, or empty when it passes."""
    if payload.get("stop_hook_active") or WAITING_SKILL.search(prompt) or QUESTION.search(prompt.strip()):
        return ""
    return asking(str(payload.get("last_assistant_message") or ""))


def main() -> None:
    if os.environ.get("CLAUDE_KEEP_GOING", "").lower() == "off":
        return
    payload = json.loads(sys.stdin.buffer.read())
    try:
        prompt = last_prompt(Path(payload["transcript_path"]))
    except (KeyError, TypeError, OSError):
        prompt = ""
    hit = verdict(payload, prompt)
    if not hit:
        return
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": stamp, "session": payload.get("session_id"), "hit": hit}) + "\n")
    json.dump({"decision": "block", "reason": REASON.format(hit=hit)}, sys.stdout)


if __name__ == "__main__":
    logging.basicConfig(format="%(name)s: %(message)s")
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - a guard must never break the session
        logging.getLogger("keep_going").error("%s: %s", type(exc).__name__, exc)
    sys.exit(0)
