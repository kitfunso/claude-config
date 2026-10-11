"""Tests for the sub-agent contract hook: the SubagentStart notice and the Opus spawn guard.

Run: python -m pytest scripts/hooks/test/test_subagent_contract.py -q -p no:cacheprovider
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

import subagent_contract as sc  # noqa: E402

BUILD = "Work in the worktree at C:/x. Run npx vitest, then commit."
GUARD = "[SPAWN GUARD]"


def brief(**over: object) -> dict:
    base = {"model": "opus", "subagent_type": "typescript-pro", "description": "E9 executor", "prompt": BUILD}
    return {**base, **over}


def test_opus_build_is_caught() -> None:
    notice = sc.spawn_check(brief())
    assert isinstance(notice, str) and notice.startswith(GUARD)


def test_sonnet_and_missing_model_pass() -> None:
    assert sc.spawn_check(brief(model="sonnet")) is None
    no_model = brief()
    del no_model["model"]
    assert sc.spawn_check(no_model) is None


@pytest.mark.parametrize("kind", sorted(sc.JUDGEMENT_TYPES))
def test_judgement_types_pass(kind: str) -> None:
    assert sc.spawn_check(brief(subagent_type=kind)) is None


@pytest.mark.parametrize("desc", ["plan-eng critic r2", "Independent review of E3",
                                  "Design the retry scheme", "Diagnose CI flake"])
def test_judgement_descriptions_pass(desc: str) -> None:
    assert sc.spawn_check(brief(description=desc)) is None


@pytest.mark.parametrize("line", ["Opus because: the retry design is open.",
                                  "  Opus because: the retry design is open.",
                                  "- Opus because: the retry design is open."])
def test_opus_because_line_keeps_opus(line: str) -> None:
    assert sc.spawn_check(brief(prompt=BUILD + "\n" + line)) is None


def test_opus_because_mid_sentence_keeps_opus() -> None:
    assert sc.spawn_check(brief(prompt=BUILD + " Opus because: the retry design is open.")) is None


@pytest.mark.parametrize("mention", ["add a line `Opus because: <what is still open in the design>` to the brief.",
                                     "No `Opus because:` line is needed for this one."])
def test_quoted_template_is_not_a_reason(mention: str) -> None:
    notice = sc.spawn_check(brief(prompt=BUILD + " " + mention))
    assert notice is not None and notice.startswith(GUARD)


def test_empty_opus_because_is_still_caught() -> None:
    reason = sc.spawn_check(brief(prompt=BUILD + "\nOpus because:"))
    assert reason is not None and reason.startswith(GUARD)


def test_orchestrator_phrase_at_head_passes() -> None:
    assert sc.spawn_check(brief(prompt="Run ONE /dev-framework-rl episode on the repo. " + BUILD)) is None


def test_orchestrator_phrase_past_head_is_caught() -> None:
    filler = (BUILD + " ") * (1600 // len(BUILD) + 1)
    assert len(filler) > sc.ORCHESTRATOR_HEAD
    reason = sc.spawn_check(brief(prompt=filler + "Run ONE /dev-framework-rl episode on the repo."))
    assert reason is not None and reason.startswith(GUARD)


@pytest.mark.parametrize("prompt", ["Run npx vitest and report the count.",
                                    "Draft section 2 on the notes branch."])
def test_needs_both_tests_and_workspace(prompt: str) -> None:
    assert sc.spawn_check(brief(prompt=prompt)) is None


def test_pre_tool_use_moves_agent_build_to_sonnet(monkeypatch: pytest.MonkeyPatch) -> None:
    # The real recorder writes telemetry, so it is stubbed out.
    monkeypatch.setattr(sc, "record", lambda **kw: None)
    out = sc.pre_tool_use({"tool_name": "Agent", "tool_input": brief()})
    assert out is not None
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse"
    # updatedInput replaces the whole input, so every other field has to ride along.
    assert spec["updatedInput"] == {**brief(), "model": "sonnet"}
    assert spec["additionalContext"].startswith(GUARD)
    assert "permissionDecision" not in spec


def test_pre_tool_use_leaves_kept_opus_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc, "record", lambda **kw: None)
    kept = brief(prompt=BUILD + "\nOpus because: the retry design is open.")
    assert sc.pre_tool_use({"tool_name": "Agent", "tool_input": kept}) is None


def test_pre_tool_use_ignores_other_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc, "record", lambda **kw: None)
    assert sc.pre_tool_use({"tool_name": "Bash", "tool_input": brief()}) is None


def run_hook(stdin: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(HOOKS / "subagent_contract.py")], input=stdin,
                          capture_output=True, text=True, env={**os.environ, **env})


START = json.dumps({"hook_event_name": "SubagentStart", "agent_id": "a1", "agent_type": "worker"})


def test_subprocess_subagent_start_prints_contract() -> None:
    proc = run_hook(START)
    spec = json.loads(proc.stdout)["hookSpecificOutput"]
    assert spec["hookEventName"] == "SubagentStart"
    assert spec["additionalContext"].startswith("[SUB-AGENT CONTRACT]")


def test_subprocess_bash_pre_tool_use_prints_nothing() -> None:
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {}})
    assert run_hook(payload).stdout == ""


def test_subprocess_bad_json_is_silent() -> None:
    proc = run_hook("not json")
    assert proc.stdout == "" and proc.returncode == 0


def test_subprocess_env_off_is_silent() -> None:
    assert run_hook(START, CLAUDE_SUBAGENT_CONTRACT="off").stdout == ""
