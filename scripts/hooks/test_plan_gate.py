#!/usr/bin/env python3
"""Self-check for the plan gate: `python test_plan_gate.py`."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("plan_gate", HERE / "plan_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def assistant(*blocks: dict, side: bool = False) -> dict:
    return {"type": "assistant", "isSidechain": side, "message": {"content": list(blocks)}}


def skill(name: str) -> dict:
    return {"type": "tool_use", "name": "Skill", "id": "t", "input": {"skill": name}}


def verdict(rows: list[dict], tool: str = "ExitPlanMode") -> dict | None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return gate.decide({"tool_name": tool, "transcript_path": str(path)})


def main() -> None:
    mention = {"type": "user", "message": {"content": "please install html-plan"}}
    assert verdict([mention]), "a mention alone must deny"
    assert verdict([assistant(skill("brainstorming"))]), "another skill must deny"
    assert verdict([assistant(skill("html-plan"), side=True)]), "a sub-agent call must deny"
    assert verdict([assistant(skill("html-plan"))]) is None, "a Skill call must pass"
    assert verdict([assistant(skill("html-plan:html-plan"))]) is None, "a plugin-prefixed call must pass"
    typed = {"type": "user", "message": {"content": "<command-name>/html-plan</command-name>"}}
    assert verdict([typed]) is None, "a typed /html-plan must pass"
    assert verdict([mention], tool="Bash") is None, "other tools are not gated"
    assert gate.decide({"tool_name": "ExitPlanMode"}) is None, "no transcript must pass"
    print("plan_gate: ok")


if __name__ == "__main__":
    main()
