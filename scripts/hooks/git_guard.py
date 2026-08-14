#!/usr/bin/env python3
"""PreToolUse hook (Bash|PowerShell): backstop for two Git rules in CLAUDE.md.

1. Branch pre-check — before any state-changing git command, inject the current
   branch of the target repo into context, so "always run git branch first"
   holds even when the model forgets.
2. Commit-message lint — on `git commit`, scan the command text for banned
   AI-isms (Stop Slop list) and warn so the model rewrites before committing.

Contract: reads hook JSON on stdin, writes hook JSON on stdout, always exits 0.
Warn-only — this hook never blocks a command; a broken guard must not break
the session.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

MUTATING = re.compile(
    r"\bgit\b[^|&;]*?\b(commit|push|merge|rebase|reset|checkout|switch|revert|"
    r"cherry-pick|tag|stash|am|pull|branch\s+-[dDmM])\b"
)

DASH_C = re.compile(r"\bgit\s+(?:[^\s]+\s+)*?-C\s+\"?([^\s\"]+)\"?")

# High-precision subset of the CLAUDE.md Banned AI-isms list. Whole words only.
# "harness" and "enhance" are omitted: too many legitimate technical uses.
BANNED_WORDS = re.compile(
    r"\b(canonical|delve|leverage|robust|seamless|holistic|crucial|pivotal|"
    r"foster|unlock|empower|elevate|streamline|meticulous|intricate|nuanced|"
    r"vibrant|tapestry|realm|underscore|showcase|boast|notably|surpass|garner|"
    r"strategically|moreover|furthermore)\b",
    re.IGNORECASE,
)
BANNED_PHRASES = re.compile(
    r"(dive into|unpack th|it's worth noting|in conclusion)", re.IGNORECASE
)


def current_branch(directory: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return "NOT A GIT REPOSITORY"
    return out.stdout.strip() or None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in command:
        return

    notes: list[str] = []

    if MUTATING.search(command):
        m = DASH_C.search(command)
        directory = m.group(1) if m else payload.get("cwd") or "."
        branch = current_branch(directory)
        if branch:
            notes.append(f"[GIT GUARD] Branch in {directory}: {branch}. "
                         "Confirm this is the intended branch before the operation.")

    if re.search(r"\bgit\b[^|&;]*\bcommit\b", command):
        hits = sorted({w.lower() for w in BANNED_WORDS.findall(command)})
        hits += [p for p in ("dive into", "it's worth noting", "in conclusion")
                 if BANNED_PHRASES.search(command) and p in command.lower()]
        if hits:
            notes.append("[GIT GUARD] Commit text contains banned AI-isms: "
                         + ", ".join(sorted(set(hits)))
                         + ". Rewrite the message per the Banned AI-isms rule "
                           "unless a word is a quoted identifier from the code.")

    if notes:
        print(json.dumps({
            "suppressOutput": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "\n".join(notes),
            },
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
