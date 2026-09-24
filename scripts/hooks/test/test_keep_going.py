"""Tests for the keep_going Stop hook and the bare-go sentence do_it_properly.py adds.

Run: python -m pytest scripts/hooks/test -q -p no:cacheprovider
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

import do_it_properly  # noqa: E402
import keep_going as hook  # noqa: E402

ALL_DONE = "<command-message>all-done</command-message>\n<command-name>/all-done</command-name>\n<command-args>?</command-args>"
ASK = "Chart rebuilt. Say go and I'll rerun the model."


def human(text: str) -> dict:
    return {"type": "user", "isSidechain": False, "origin": {"kind": "human"},
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def transcript(tmp_path: Path, prompt: str) -> Path:
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps(human(prompt), separators=(",", ":")) + "\n", encoding="utf-8")
    return path


def stop_payload(path: Path, reply: str, active: bool = False) -> dict:
    return {"session_id": "s1", "transcript_path": str(path), "cwd": str(path.parent),
            "hook_event_name": "Stop", "stop_hook_active": active, "last_assistant_message": reply}


def run(script: str, payload: object, **env: str) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    full_env = {**os.environ, "CLAUDE_KEEP_GOING": "", "CLAUDE_DO_IT_PROPERLY": "", **env}
    return subprocess.run([sys.executable, str(HOOKS / script)], input=data, capture_output=True,
                          env=full_env, timeout=30)


class TestAsking:
    @pytest.mark.parametrize(("reply", "hit"), [
        ("Nothing is built yet. Go?", "Go?"),
        ("Say go and I'll open the report.", "Say go"),
        ("Tests pass. Want me to fix the other two?", "Want me to"),
        ("The chart is fixed.\n**Next:** Task 11, the legend.", "Next:"),
        ('Reply "apply consolidated" and I\'ll patch the plan.', 'Reply "apply'),
        ("The deploy is done. Should I tidy the page?", "Should I"),
        ("Say go and I'll build it. It drops one record at midnight, which costs nothing.", "Say go"),
        ("The rows are fixed. The page shows them after the next scheduled run.", "next scheduled"),
        ("Tell me if you want the old folder kept.", "me if you want"),
        ("Tests pass.\nThen I'll write the amendment and the git commands.", "Then I'll"),
    ])
    def test_a_reply_that_ends_on_an_ask_is_caught(self, reply: str, hit: str) -> None:
        assert hook.asking(reply) == hit

    @pytest.mark.parametrize("reply", [
        'Say "go deploy" and I\'ll ship it to the VM.',
        "Say go and I'll send it to the external tracker.",
        "Should I push it to origin?",
        "Next is Task 7. That step needs compliance approval first.",
        "I say yes; the hook is worth it.",
        "Say A or B and I'll carry on.",
        'Say "go 1" or "go 2".',
        "Should I keep the log, or switch to the tool?",
        "Tell me when it has run and I will re-hash the VM.",
        "The watcher is running. When it finishes I'll report the numbers, next is the page.",
        "Set them in git config if you want that to match.",
        "Done: 128 tests pass and the hook is wired.",
        "Paste this:\n```\nsay go\n```\nThat is the whole change.",
        "Should I fix it?\nThe fix is in.\nTests pass.",
    ])
    def test_a_plain_report_or_a_real_reason_to_stop_passes(self, reply: str) -> None:
        assert hook.asking(reply) == ""


class TestVerdict:
    def test_the_second_stop_always_passes(self) -> None:
        assert hook.verdict({"last_assistant_message": ASK}, "rebuild the chart") == "Say go"
        assert hook.verdict({"last_assistant_message": ASK, "stop_hook_active": True}, "rebuild the chart") == ""

    def test_a_skill_that_waits_for_keith_passes(self) -> None:
        assert hook.verdict({"last_assistant_message": ASK}, ALL_DONE) == ""
        assert hook.verdict({"last_assistant_message": ASK}, "<command-name>/grill-me</command-name>") == ""

    @pytest.mark.parametrize(("prompt", "hit"), [
        ("how did the model do against the baseline?", ""),
        ("explain why any of these matter in plain English", ""),
        ("progress?", "Say go"),
        ("continue", "Say go"),
    ])
    def test_an_answer_to_a_question_passes_but_a_poke_does_not(self, prompt: str, hit: str) -> None:
        assert hook.verdict({"last_assistant_message": ASK}, prompt) == hit


class TestMain:
    def test_an_ask_is_blocked_once_and_logged(self, tmp_path: Path) -> None:
        path = transcript(tmp_path, "rebuild the chart")
        out = run("keep_going.py", stop_payload(path, ASK), CLAUDE_CONFIG_DIR=str(tmp_path))
        decision = json.loads(out.stdout)
        assert out.returncode == 0 and decision["decision"] == "block" and "'Say go'" in decision["reason"]
        rec = json.loads((tmp_path / "state" / "keep_going.jsonl").read_text(encoding="utf-8"))
        assert list(rec) == ["ts", "session", "hit"] and (rec["session"], rec["hit"]) == ("s1", "Say go")
        again = run("keep_going.py", stop_payload(path, ASK, active=True), CLAUDE_CONFIG_DIR=str(tmp_path))
        assert (again.returncode, again.stdout) == (0, b"")

    def test_a_plain_report_and_an_all_done_turn_pass_silently(self, tmp_path: Path) -> None:
        plain = run("keep_going.py", stop_payload(transcript(tmp_path, "rebuild it"), "Rebuilt; 12 tests pass."),
                    CLAUDE_CONFIG_DIR=str(tmp_path))
        gate = run("keep_going.py", stop_payload(transcript(tmp_path, ALL_DONE), "NO\n\nWant me to fix it?"),
                   CLAUDE_CONFIG_DIR=str(tmp_path))
        assert (plain.returncode, plain.stdout, gate.returncode, gate.stdout) == (0, b"", 0, b"")
        assert not (tmp_path / "state").exists()

    def test_bad_input_and_the_escape_hatch_never_block(self, tmp_path: Path) -> None:
        bad = run("keep_going.py", b"not json", CLAUDE_CONFIG_DIR=str(tmp_path))
        assert (bad.returncode, bad.stdout) == (0, b"") and bad.stderr.startswith(b"keep_going: ")
        off = run("keep_going.py", stop_payload(transcript(tmp_path, "rebuild it"), ASK),
                  CLAUDE_CONFIG_DIR=str(tmp_path), CLAUDE_KEEP_GOING="off")
        assert (off.returncode, off.stdout) == (0, b"") and not (tmp_path / "state").exists()

    def test_a_missing_transcript_still_checks_the_reply(self, tmp_path: Path) -> None:
        out = run("keep_going.py", stop_payload(tmp_path / "gone.jsonl", ASK), CLAUDE_CONFIG_DIR=str(tmp_path))
        assert json.loads(out.stdout)["decision"] == "block"


class TestBareGo:
    @pytest.mark.parametrize("prompt", ["go", "continue", "Yes, carry on", "apply consolidated"])
    def test_a_bare_go_adds_the_keep_going_sentence(self, prompt: str) -> None:
        expected = f"{do_it_properly.RULE}\n{do_it_properly.BARE_GO}"
        assert do_it_properly.context(json.dumps({"prompt": prompt})) == expected

    @pytest.mark.parametrize("raw", [
        json.dumps({"prompt": "build the scorecard"}),
        json.dumps({"prompt": "yes, and also change every button on the settings page to blue"}),
        json.dumps({"prompt": ""}),
        "not json",
        "[]",
    ])
    def test_anything_else_gets_the_rule_alone(self, raw: str) -> None:
        assert do_it_properly.context(raw) == do_it_properly.RULE

    def test_the_script_adds_it_too(self) -> None:
        out = run("do_it_properly.py", {"session_id": "s1", "prompt": "go"})
        context = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
        assert out.returncode == 0 and context.endswith(do_it_properly.BARE_GO)
