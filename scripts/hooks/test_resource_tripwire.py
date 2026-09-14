#!/usr/bin/env python3
"""Self-check for the tripwire's deadline scan: `python test_resource_tripwire.py`.

The break must never report more bytes than it parsed, or the cached offset skips
un-scanned transcript lines and the counters silently undercount forever.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(budget: str) -> object:
    import os
    os.environ["TRIPWIRE_BUDGET_S"] = budget
    spec = importlib.util.spec_from_file_location("rt", HERE / "resource_tripwire.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def line(name: str) -> bytes:
    rec = {"message": {"content": [{"type": "tool_use", "name": name, "id": name, "input": {}}]}}
    return json.dumps(rec).encode("utf-8")


def main() -> None:
    data = b"\n".join(line(f"Bash{i}") for i in range(20000)) + b"\n"

    m = load("60")
    blocks: list[dict] = []
    used = m.scan(data, blocks)
    assert used == len(data), f"full scan consumed {used} of {len(data)}"
    assert len(blocks) == 20000, len(blocks)

    m = load("-1")  # already past the deadline: break on the first check
    blocks = []
    used = m.scan(data, blocks)
    assert used == 0, f"expired budget consumed {used} bytes"
    assert blocks == [], blocks

    assert m.count_tools([{"name": "Bash"}, {"name": "Bash"}, {"name": "Skill"}]) == {"Bash": 2, "Skill": 1}
    fable_guard(m)
    print("ok")


def user(text: object) -> bytes:
    return json.dumps({"type": "user", "message": {"content": text}}).encode("utf-8")


def asst(model: str, tool: str) -> bytes:
    rec = {"type": "assistant", "message": {"model": model,
           "content": [{"type": "tool_use", "name": tool, "id": tool, "input": {}}]}}
    return json.dumps(rec).encode("utf-8")


def fable_guard(m: object) -> None:
    """Markers land in the scan; the deny fires at budget+1, resets on a human turn or Agent."""
    m = load("60")  # the caller's module is past its deadline
    m.FABLE_EXEC_BUDGET = "3"
    data = b"\n".join([user("go"), asst("claude-fable-5-1", "Bash"), asst("claude-fable-5-1", "Edit"),
                       user([{"type": "text", "text": "<task-notification>x"}]),
                       asst("claude-fable-5-1", "Read")]) + b"\n"
    blocks: list[dict] = []
    m.scan(data, blocks)
    assert m.current_model(blocks) == "claude-fable-5-1", blocks
    assert m.count_tools(blocks) == {"Bash": 1, "Edit": 1, "Read": 1}, blocks
    assert m.exec_calls_this_leg(blocks) == 2, blocks  # task notifications never reset

    main = {"tool_name": "Bash"}
    assert m.fable_guard(main, blocks) is None  # call 3 of 3
    blocks.append({"name": "mcp__claude-in-chrome__computer"})
    denied = m.fable_guard(main, blocks)
    assert denied and "FABLE ORCHESTRATOR" in denied["hookSpecificOutput"]["permissionDecisionReason"]
    assert m.fable_guard({"tool_name": "Bash", "agent_id": "a1"}, blocks) is None  # sub-agent
    blocks.append({"name": "Agent"})
    assert m.fable_guard(main, blocks) is None  # a delegation resets the leg
    blocks.append({"name": "__user__"})
    assert m.exec_calls_this_leg(blocks) == 0

    sonnet: list[dict] = []
    m.scan(b"\n".join([user("go")] + [asst("claude-sonnet-5", "Bash")] * 9) + b"\n", sonnet)
    assert m.fable_guard(main, sonnet) is None  # only Fable is budgeted
    m.FABLE_EXEC_BUDGET = "off"
    assert m.fable_guard(main, blocks + [{"name": "Bash"}] * 9) is None


if __name__ == "__main__":
    main()
