#!/usr/bin/env python3
"""PreToolUse hook (Edit|Write): backstop for the Comments rule in
rules/coding-standards.md. Python port of the home box's comment-budget-guard.js.

Denies the write before the file is touched when the new content has:
  - more than 3 comment lines in a row, or
  - more than 20% comment density, once the content is 15+ lines.

Skips markdown, JSON, config files, anything under docs/, Python docstrings
(only `#` lines count), and JSDoc blocks carrying @param / @returns.
Escape hatch: CLAUDE_COMMENT_BUDGET=off.

Contract: reads hook JSON on stdin, writes hook JSON on stdout. Fails open —
a broken guard must not break the session.
"""

from __future__ import annotations

import json
import os
import re
import sys

MAX_RUN = 3
MAX_DENSITY = 0.20
MIN_LINES_FOR_DENSITY = 15

SKIP_EXTENSIONS = {
    ".md", ".markdown", ".rst", ".txt", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".env", ".csv", ".html", ".xml", ".lock",
}
HASH_COMMENT = {".py", ".sh", ".bash", ".ps1", ".r", ".rb", ".pl", ".cmake"}
SLASH_COMMENT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".c", ".h", ".cpp",
    ".hpp", ".cs", ".go", ".rs", ".swift", ".kt", ".scala", ".css", ".scss",
}
DASH_COMMENT = {".sql"}


def comment_flags(lines: list[str], ext: str) -> list[bool]:
    flags = [False] * len(lines)
    if ext in HASH_COMMENT:
        for i, line in enumerate(lines):
            stripped = line.strip()
            flags[i] = stripped.startswith("#") and not stripped.startswith("#!")
    elif ext in DASH_COMMENT:
        for i, line in enumerate(lines):
            flags[i] = line.strip().startswith("--")
    elif ext in SLASH_COMMENT:
        in_block = False
        block_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if in_block:
                flags[i] = True
                if "*/" in stripped:
                    in_block = False
                    if any("@param" in lines[j] or "@returns" in lines[j] for j in range(block_start, i + 1)):
                        for j in range(block_start, i + 1):
                            flags[j] = False
                continue
            if stripped.startswith("//"):
                flags[i] = True
            elif stripped.startswith("/*"):
                flags[i] = True
                block_start = i
                if "*/" in stripped:
                    if "@param" in stripped or "@returns" in stripped:
                        flags[i] = False
                else:
                    in_block = True
    return flags


def check(content: str, ext: str) -> str | None:
    lines = content.splitlines()
    if not lines:
        return None
    flags = comment_flags(lines, ext)

    run = 0
    for flag in flags:
        run = run + 1 if flag else 0
        if run > MAX_RUN:
            return (
                f"more than {MAX_RUN} comment lines in a row — the Comments rule "
                "(rules/coding-standards.md) allows one line, two at most, WHY not "
                "WHAT. Cut the block, then retry. Escape: CLAUDE_COMMENT_BUDGET=off."
            )

    total = len(lines)
    count = sum(flags)
    if total >= MIN_LINES_FOR_DENSITY and count / total > MAX_DENSITY:
        return (
            f"comment density {count}/{total} = {count / total:.0%} exceeds "
            f"{MAX_DENSITY:.0%} — the Comments rule (rules/coding-standards.md) "
            "says one line, two at most, WHY not WHAT. Trim comments, then retry. "
            "Escape: CLAUDE_COMMENT_BUDGET=off."
        )
    return None


def main() -> None:
    if os.environ.get("CLAUDE_COMMENT_BUDGET", "").lower() == "off":
        return
    payload = json.load(sys.stdin)
    if payload.get("tool_name") not in ("Edit", "Write"):
        return
    tool_input = payload.get("tool_input") or {}
    file_path = (tool_input.get("file_path") or "").replace("\\", "/")
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SKIP_EXTENSIONS or ext not in (HASH_COMMENT | SLASH_COMMENT | DASH_COMMENT):
        return
    if re.search(r"(^|/)docs(/|$)", file_path, re.IGNORECASE):
        return
    content = tool_input.get("content") or tool_input.get("new_string") or ""
    reason = check(content, ext)
    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
