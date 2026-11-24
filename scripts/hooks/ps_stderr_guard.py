#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys

REDIRECT = re.compile(r"2>\s*&\s*1")
REASON = (
    "ps-stderr-guard: 2>&1 in PowerShell 5.1 wraps native-exe stderr in "
    "NativeCommandError and reports failure even on exit 0. stderr is already "
    "captured: run the command bare, or use the Bash tool for stream routing."
)


def main() -> None:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "PowerShell":
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not REDIRECT.search(command):
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
