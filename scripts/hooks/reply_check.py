#!/usr/bin/env python3
"""Stop hook: measures every reply against four CLAUDE.md rules and logs one JSON line.

Flags: long, table, bullets and banned:<word> (Human Voice); sweeping (Do It Properly);
unsourced-numbers (Sourcing); no-diagnosis (Root Cause). Text inside ``` fences and
`inline code` is never scanned; each inline span counts as one word. Never blocks: a
Stop block cannot un-show a reply, it only makes Claude print a second one, so the
feedback reaches the next turn through human_voice.py, which imports feedback().
The log (~/.claude/state/reply_check.jsonl) holds counts and flags, never reply text;
"tools" is null when the transcript cannot be read. Escape hatch: CLAUDE_REPLY_CHECK=off.
Always exits 0, with one stderr line naming any error; a broken guard must not break the session.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

try:
    from git_guard import BANNED_PHRASES, BANNED_WORDS
except Exception:  # noqa: BLE001 - a broken git_guard costs the banned-word check, not the hook
    BANNED_WORDS = BANNED_PHRASES = re.compile(r"(?!)")

LOG = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "state" / "reply_check.jsonl"
TRANSCRIPT_TAIL = 4 << 20
LOG_TAIL = 64 << 10
MAX_LINES = 8
MAX_WORDS = 220
BULLET_RUN = 6
MIN_NUMBERS = 2
EDIT_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

INLINE_CODE = re.compile(r"`[^`\n]+`")
TABLE_RULE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+(?:\s*:?-{3,}:?\s*)?$")
LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+\S")
LIST_MARKER = re.compile(r"^[ \t]*\d+[.)][ \t]+", re.M)
WORD_TAIL = re.compile(r"\w*")
SWEEPING = re.compile(r"\b(?:tried everything|every table|all tables|all notebooks)\b", re.I)
DEPTH = re.compile(r"\b(?:in detail|in[ -]depth|detailed|full report|walk me through|long[ -]form|go long)\b",
                   re.I)
# "fixture" is a freight term on this desk, not a fix-it ask.
FIX_IT = re.compile(r"\b(?:fix(?!ture)|bug|broken|crash|error|fails|failing)"
                    r"|does(?:n['’]t| not) work|n(?:o|['’])t working", re.I)
MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
         r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?")
NOT_A_QUANTITY = re.compile("|".join((
    r"\b\d{4}-\d\d-\d\d(?:[T ]\d\d:\d\d(?::\d\d(?:\.\d+)?)?Z?)?",
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?[ -]{MONTH}(?:,?[ -]\d{{4}}\b)?",
    rf"\b{MONTH} \d{{1,2}}(?:st|nd|rd|th)?\b(?:,? \d{{4}}\b)?",
    rf"\b{MONTH} \d{{4}}\b",
    r"\b(?:19|20)\d\ds?\b",
    r"\b\d{1,2}:\d\d(?::\d\d)?(?:\s?[ap]\.?m\b\.?)?",
    r"\b\d{1,2}\s?[ap]m\b",
    r"\bv?\d+(?:\.\d+){2,}\S*",
    r"\b(?=[\da-f]*[a-f])(?=[\da-f]*\d)[\da-f]{7,40}\b",
    r"[\w.\\/-]*\.\w+:\d+(?:[-:]\d+)?",
    r"\b\d+(?:st|nd|rd|th)\b",
)), re.I)
NUMBER = re.compile(r"(?<![\w.:/#-])[-+~]?[$£€]?\d[\d,]*(?:\.\d+)?")

FLAG_WORDS = {
    "table": "a table",
    "bullets": f"a bullet wall ({BULLET_RUN}+ list lines in a row)",
    "sweeping": "a sweeping claim ('tried everything', 'every table') that needs the list of what was covered",
    "unsourced-numbers": "numbers with no tool call that turn",
    "no-diagnosis": "edits on a fix-it prompt with no <diagnosis> block",
}


# NamedTuple, not dataclass: human_voice imports this module on every prompt and
# dataclasses drags in inspect.
class Turn(NamedTuple):
    """What the transcript says about the turn: the human prompt, its tool calls, any <diagnosis>."""

    prompt: str
    tools: tuple[str, ...]
    diagnosed: bool


def prose(reply: str) -> list[str]:
    """Non-blank reply lines outside ``` fences, each `inline code` span cut to one token."""
    kept: list[str] = []
    fenced = False
    for line in reply.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.strip():
            kept.append(INLINE_CODE.sub("CODE", line))
    return kept


def has_table(lines: list[str]) -> bool:
    return any("|" in head and TABLE_RULE.match(rule) for head, rule in zip(lines, lines[1:]))


def longest_list_run(lines: list[str]) -> int:
    """Indented continuation lines keep a run going; any other prose line ends it."""
    best = run = 0
    for line in lines:
        if LIST_ITEM.match(line):
            run += 1
            best = max(best, run)
        elif not line[:1].isspace():
            run = 0
    return best


def banned(text: str) -> list[str]:
    """git_guard's list; a phrase cut mid-word ('unpack th') is completed to the word."""
    hits = {word.lower() for word in BANNED_WORDS.findall(text)}
    for m in BANNED_PHRASES.finditer(text):
        hits.add((m.group(0) + WORD_TAIL.match(text, m.end()).group(0)).lower())
    return sorted(hits)


def count_numbers(text: str) -> int:
    """Numeric tokens left once dates, times, versions, hashes, file:line refs and list markers go."""
    return len(NUMBER.findall(NOT_A_QUANTITY.sub(" ", LIST_MARKER.sub("", text))))


def measure(reply: str, turn: Turn | None) -> dict:
    """Counts and flags for one reply; a None turn skips the checks that need the transcript."""
    lines = prose(reply)
    text = "\n".join(lines)
    words = sum(1 for token in text.split() if any(c.isalnum() for c in token))
    prompt = turn.prompt if turn else ""
    flags: list[str] = []
    if (len(lines) > MAX_LINES or words > MAX_WORDS) and not DEPTH.search(prompt):
        flags.append("long")
    if has_table(lines):
        flags.append("table")
    if longest_list_run(lines) >= BULLET_RUN:
        flags.append("bullets")
    flags += [f"banned:{hit}" for hit in banned(text)]
    if SWEEPING.search(text):
        flags.append("sweeping")
    if turn is not None and not turn.tools and count_numbers(text) >= MIN_NUMBERS:
        flags.append("unsourced-numbers")
    if (turn is not None and FIX_IT.search(prompt) and EDIT_TOOLS.intersection(turn.tools)
            and not (turn.diagnosed or "<diagnosis>" in reply)):
        flags.append("no-diagnosis")
    return {"lines": len(lines), "words": words,
            "tools": None if turn is None else len(turn.tools), "flags": flags}


def read_tail(path: Path, size: int) -> list[bytes]:
    """Whole lines from the last `size` bytes; transcripts reach hundreds of MB."""
    with path.open("rb") as fh:
        end = fh.seek(0, os.SEEK_END)
        fh.seek(max(0, end - size))
        lines = fh.read().split(b"\n")
    return lines[1:] if end > size else lines


def parse(raw: bytes) -> dict:
    try:
        row = json.loads(raw)
    except ValueError:
        return {}
    return row if isinstance(row, dict) else {}


def text_of(row: dict) -> str:
    content = (row.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return "\n".join(str(b.get("text") or "") for b in content or []
                     if isinstance(b, dict) and b.get("type") == "text")


def split_turn(lines: list[bytes]) -> tuple[dict | None, list[bytes]]:
    """The last main-thread human prompt and the raw rows after it; with no prompt in
    the tail, every row counts as the turn."""
    for i in range(len(lines) - 1, -1, -1):
        if b'"human"' in lines[i]:
            row = parse(lines[i])
            if (row.get("type") == "user" and not row.get("isSidechain")
                    and (row.get("origin") or {}).get("kind") == "human"):
                return row, lines[i + 1:]
    return None, lines


def last_prompt(transcript: Path) -> str:
    """Text of the latest human prompt in the transcript tail; empty when none is found."""
    row, _ = split_turn(read_tail(transcript, TRANSCRIPT_TAIL))
    return text_of(row) if row else ""


def load_turn(transcript: Path) -> Turn:
    prompt_row, rows = split_turn(read_tail(transcript, TRANSCRIPT_TAIL))
    tools: list[str] = []
    diagnosed = False
    # A byte probe before json.loads keeps a 4 MB tail inside the 150 ms budget.
    for raw in rows:
        if b'"tool_use"' not in raw and b"<diagnosis>" not in raw:
            continue
        row = parse(raw)
        if row.get("type") != "assistant" or row.get("isSidechain"):
            continue
        for block in (row.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                tools.append(str(block.get("name")))
            elif block.get("type") == "text" and "<diagnosis>" in str(block.get("text")):
                diagnosed = True
    return Turn(text_of(prompt_row) if prompt_row else "", tuple(tools), diagnosed)


def describe(record: dict) -> str:
    """One plain sentence naming each flag on a log record; empty when the reply was clean."""
    flags = [str(flag) for flag in record.get("flags") or []]
    parts: list[str] = []
    if "long" in flags:
        lines, words = int(record.get("lines") or 0), int(record.get("words") or 0)
        if lines > MAX_LINES:
            parts.append(f"{lines} lines (limit {MAX_LINES})")
        if words > MAX_WORDS or lines <= MAX_LINES:
            parts.append(f"{words} words (limit {MAX_WORDS})")
    parts += [FLAG_WORDS[flag] for flag in flags if flag in FLAG_WORDS]
    hits = [flag.split(":", 1)[1] for flag in flags if flag.startswith("banned:")]
    if hits:
        parts.append(f"banned word{'s' if len(hits) > 1 else ''} ({', '.join(hits)})")
    return f"Your last reply was flagged: {', '.join(parts)}." if parts else ""


def feedback(session_id: str) -> str:
    """The flag sentence for this session's last logged reply, read from the log's tail."""
    if not session_id or os.environ.get("CLAUDE_REPLY_CHECK", "").lower() == "off":
        return ""
    try:
        rows = read_tail(LOG, LOG_TAIL)
    except OSError:
        return ""
    needle = json.dumps(session_id).encode()
    for raw in reversed(rows):
        record = parse(raw) if needle in raw else {}
        if record.get("session") == session_id:
            try:
                return describe(record)
            except (TypeError, ValueError, AttributeError):
                return ""
    return ""


def main() -> None:
    if os.environ.get("CLAUDE_REPLY_CHECK", "").lower() == "off":
        return
    payload = json.loads(sys.stdin.buffer.read())
    try:
        turn: Turn | None = load_turn(Path(payload["transcript_path"]))
    except (KeyError, TypeError, OSError):
        turn = None
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
              "session": payload.get("session_id"),
              **measure(str(payload.get("last_assistant_message") or ""), turn)}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - a guard must never break the session
        print(f"reply_check: {type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(0)
