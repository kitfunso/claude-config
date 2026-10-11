#!/usr/bin/env python3
"""Sub-agent contract: a SubagentStart notice, and a spawn guard on the Agent tool.

The guard moves an Opus spawn to Sonnet when its brief is a code build with a test
check; `Opus because: <reason>` in the brief keeps Opus. Measurements: docs/incidents.md, 2026-10-08.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
try:
    from record_component import record
except ImportError:  # the recorder is optional, the guard is not
    def record(**_: object) -> None:
        return None

CONTRACT = (
    "[SUB-AGENT CONTRACT] Your whole context is re-sent on every call you make, so calls are the cost.\n"
    "1. Batch: send independent Read, Grep and Glob calls in one message. Read the line range you "
    "need, not the whole file.\n"
    "2. Do not wait on CI or a remote job: no `until ... sleep` loop, no `--watch`. Push, say what "
    "to watch and return. A wait over 5 minutes re-bills your whole context.\n"
    "3. One slice: when the check in your brief passes, stop. Commit what you changed and return "
    "what is done, what remains and the next step with file:line."
)
# Reviews, planning, design and unknown-cause debugging stay on Opus under the routing rule.
JUDGEMENT_TYPES = frozenset({"senior-code-reviewer", "debugger", "Plan", "Explore"})
JUDGEMENT = re.compile(r"critic|critique|review|audit|verdict|grill|red.?team|\bscore\b|\bdesign\b|research"
                       r"|prereg|draft|diagnos|investigat|survey", re.I)
ORCHESTRATOR = re.compile(r"/dev-framework-rl|Skill tool|orchestrat", re.I)
ORCHESTRATOR_HEAD = 1500  # an orchestrator brief says so at the top; later mentions are context
TESTS = re.compile(r"vitest|pytest|npm (run )?test|\btsc\b|red-first|test-first|\btests?\b", re.I)
WORKSPACE = re.compile(r"worktree|\bbranch\b|\bcommit", re.I)
# The notice's own `<...>` template and a bare backticked mention are not reasons.
KEEP_OPUS = re.compile(r"\bopus because:(?!`)\s*[^\s<]", re.I)
MOVE_NOTICE = (
    "[SPAWN GUARD] This agent was moved from opus to sonnet. Its brief is a code build with a test "
    "check (it names tests and a worktree, branch or commit), and a build from a complete brief runs "
    "on sonnet (CLAUDE.md, Sub-agents). To keep Opus, add a line `Opus because: <what is still open "
    "in the design>` to the brief."
)


def spawn_check(tool_input: dict) -> str | None:
    """Return the notice for an Opus code build that gives no reason for Opus, else None."""
    if tool_input.get("model") != "opus":
        return None
    if tool_input.get("subagent_type") in JUDGEMENT_TYPES:
        return None
    prompt = str(tool_input.get("prompt") or "")
    if JUDGEMENT.search(str(tool_input.get("description") or "")) or KEEP_OPUS.search(prompt):
        return None
    if ORCHESTRATOR.search(prompt[:ORCHESTRATOR_HEAD]):
        return None
    if TESTS.search(prompt) and WORKSPACE.search(prompt):
        return MOVE_NOTICE
    return None


def pre_tool_use(payload: dict) -> dict | None:
    if payload.get("tool_name") != "Agent":
        return None
    tool_input = payload.get("tool_input") or {}
    notice = spawn_check(tool_input)
    if notice is None:
        return None
    record(kind="hook", name=Path(__file__).name, session_id=payload.get("session_id"),
           cwd=payload.get("cwd"), notes=notice)
    # A rewrite costs the caller nothing; a deny costs a second send of the whole brief.
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "updatedInput": {**tool_input, "model": "sonnet"},
                                   "additionalContext": notice}}


def subagent_start(payload: dict) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": CONTRACT}}


def main() -> None:
    if os.environ.get("CLAUDE_SUBAGENT_CONTRACT", "").lower() == "off":
        return
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    event = payload.get("hook_event_name")
    if event == "SubagentStart":
        out = subagent_start(payload)
    elif event == "PreToolUse":
        out = pre_tool_use(payload)
    else:
        out = None
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    main()
