"""Tests for the replay harness's transcript audit and scoring."""
from __future__ import annotations

import json

from replay import audit, gain

WORK = "C:\\qmp-replays\\runs\\r1"


def use(name: str, **inp: object) -> str:
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": name, "input": inp}]}})


def result(turns: int = 7, out: int = 900) -> str:
    return json.dumps({"type": "result", "num_turns": turns, "usage": {"output_tokens": out}})


def test_own_folder_is_allowed() -> None:
    lines = [use("Bash", command="cd C:/qmp-replays/runs/r1 && python fit.py"),
             use("Read", file_path="C:\\qmp-replays\\runs\\r1\\data\\train.parquet"), result()]
    a = audit(lines, "with", (), WORK)
    assert a.void == "" and a.turns == 7 and a.output_tokens == 900


def test_sibling_run_and_case_paths_void() -> None:
    assert "qmp-replays/runs/" in audit([use("Bash", command="ls C:/qmp-replays/runs/r2")], "with", (), WORK).void
    assert "prc26" in audit([use("Glob", path="C:/Users/skf_s/prc26-final")], "with", ("prc26",), WORK).void
    assert audit([use("Read", file_path="C:\\Users\\skf_s\\.hippo\\hippo.db")], "with", (), WORK).void


def test_skill_use_counts_and_is_banned_without() -> None:
    with_arm = audit([use("Skill", skill="quant-ml-protocol"), result()], "with", (), WORK)
    assert with_arm.skill_used and with_arm.void == ""
    read = audit([use("Read", file_path="C:/Users/skf_s/.claude/skills/quant-ml-protocol/SKILL.md")],
                 "without", (), WORK)
    assert "skills/quant-ml-protocol" in read.void


def test_rubric_paths_void_even_with_the_skill() -> None:
    lines = [use("Read", file_path="C:/Users/skf_s/.claude/skills/quant-ml-protocol/replays/taxi-out/grade.py")]
    assert audit(lines, "with", (), WORK).void


def test_gain_orientation() -> None:
    assert gain(400.0, 460.0, True) == 60.0
    assert gain(0.3, 0.1, False) == 0.3 - 0.1
    assert gain(None, 460.0, True) is None
