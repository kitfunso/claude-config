"""Tests for the reply_check Stop hook and the flag sentence human_voice.py adds.

Run: python -m pytest scripts/hooks/test -q -p no:cacheprovider
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

import git_guard  # noqa: E402
import human_voice  # noqa: E402
import reply_check as hook  # noqa: E402

WITH_TOOLS = hook.Turn("check the numbers", ("Read",), False)
NO_TOOLS = hook.Turn("check the numbers", (), False)
FIX = hook.Turn("fix the crash in the loader", ("Read", "Edit"), False)
EXAMPLE = "Your last reply was flagged: 14 lines (limit 8), a table, numbers with no tool call that turn."


def flags(reply: str, turn: hook.Turn | None = WITH_TOOLS) -> list[str]:
    return hook.measure(reply, turn)["flags"]


def lines(n: int) -> str:
    return "\n".join(f"Plain line {chr(97 + i)}." for i in range(n))


def bullets(n: int, marker: str = "-") -> str:
    return "\n".join(f"{marker} item {chr(97 + i)}" for i in range(n))


def human(text: str) -> dict:
    return {"type": "user", "isSidechain": False, "origin": {"kind": "human"},
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def said(text: str) -> dict:
    return {"type": "assistant", "isSidechain": False,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


def called(name: str, sidechain: bool = False) -> dict:
    block = {"type": "tool_use", "id": f"toolu_{name}", "name": name, "input": {}}
    return {"type": "assistant", "isSidechain": sidechain, "message": {"role": "assistant", "content": [block]}}


def result(text: str) -> dict:
    block = {"type": "tool_result", "tool_use_id": "toolu_x", "content": text}
    return {"type": "user", "isSidechain": False, "message": {"role": "user", "content": [block]}}


def notification(text: str) -> dict:
    return {"type": "user", "isSidechain": False, "origin": {"kind": "task-notification"},
            "message": {"role": "user", "content": text}}


def transcript(tmp_path: Path, rows: list[dict], name: str = "session.jsonl") -> Path:
    path = tmp_path / name
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    return path


def record(session: str, flag_list: list[str], lines_: int = 3, words: int = 40) -> dict:
    return {"ts": "2026-09-24T10:00:00Z", "session": session, "lines": lines_, "words": words,
            "tools": 1, "flags": flag_list}


def write_log(path: Path, *records: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def run(script: str, payload: object, **env: str) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    full_env = {**os.environ, "CLAUDE_REPLY_CHECK": "", "CLAUDE_HUMAN_VOICE": "", **env}
    return subprocess.run([sys.executable, str(HOOKS / script)], input=data, capture_output=True,
                          env=full_env, timeout=30)


def stop_payload(path: Path, reply: str) -> dict:
    return {"session_id": "s1", "transcript_path": str(path), "cwd": str(path.parent),
            "hook_event_name": "Stop", "stop_hook_active": False, "last_assistant_message": reply}


class TestLength:
    def test_nine_lines_is_long(self) -> None:
        assert "long" in flags(lines(9))

    def test_eight_lines_is_not_long(self) -> None:
        assert "long" not in flags(lines(8))

    def test_blank_lines_do_not_count(self) -> None:
        out = hook.measure(lines(8).replace("\n", "\n\n"), WITH_TOOLS)
        assert out["lines"] == 8 and "long" not in out["flags"]

    def test_more_than_220_words_is_long(self) -> None:
        assert "long" in flags(" ".join(["word"] * 221))
        assert "long" not in flags(" ".join(["word"] * 220))

    def test_fenced_code_is_not_counted(self) -> None:
        fence = "```python\n" + "\n".join(f"x{i} = {i}" for i in range(30)) + "\n```"
        out = hook.measure(f"{lines(3)}\n{fence}\n{lines(2)}", WITH_TOOLS)
        assert out["lines"] == 5 and "long" not in out["flags"]

    def test_inline_code_counts_as_one_word(self) -> None:
        assert hook.measure("Run `python -m pytest -q` now.", WITH_TOOLS)["words"] == 3

    @pytest.mark.parametrize("ask", ["Walk me through the design", "give me the full report",
                                     "explain it in detail", "an in-depth look", "go long on this"])
    def test_a_depth_request_exempts_length(self, ask: str) -> None:
        assert "long" not in flags(lines(20), hook.Turn(ask, ("Read",), False))

    def test_depth_words_in_the_reply_do_not_exempt(self) -> None:
        assert "long" in flags(lines(12) + "\nHere it is in detail.")


class TestShape:
    def test_a_markdown_table_is_flagged(self) -> None:
        assert "table" in flags("Results:\n| run | score |\n|---|---:|\n| a | b |")
        assert "table" in flags("run | score\n:--- | ---:\na | b")

    @pytest.mark.parametrize("reply", [
        pytest.param("a | b | c\nd | e | f", id="pipes with no rule row"),
        pytest.param("Title\n---\nBody text", id="setext heading"),
        pytest.param("```\n| a | b |\n|---|---|\n```", id="table inside a fence"),
    ])
    def test_not_a_table(self, reply: str) -> None:
        assert "table" not in flags(reply)

    @pytest.mark.parametrize("marker", ["-", "*"])
    def test_six_list_lines_is_a_bullet_wall(self, marker: str) -> None:
        assert "bullets" in flags(bullets(6, marker))

    @pytest.mark.parametrize("style", ["{}. step", "{}) step"])
    def test_numbered_lists_count(self, style: str) -> None:
        assert "bullets" in flags("\n".join(style.format(i) for i in range(1, 7)))

    def test_five_list_lines_is_not_a_wall(self) -> None:
        assert "bullets" not in flags(bullets(5))

    def test_blank_lines_and_continuations_keep_a_run(self) -> None:
        assert "bullets" in flags(bullets(6).replace("\n", "\n\n"))
        assert "bullets" in flags(bullets(6).replace("\n", "\n  continued here\n"))

    def test_a_prose_line_ends_the_run(self) -> None:
        assert "bullets" not in flags(f"{bullets(3)}\nThen the second half:\n{bullets(3)}")


class TestWords:
    def test_reuses_the_git_guard_lists(self) -> None:
        assert hook.BANNED_WORDS is git_guard.BANNED_WORDS
        assert hook.BANNED_PHRASES is git_guard.BANNED_PHRASES

    def test_banned_words_and_phrases_are_flagged(self) -> None:
        out = flags("A Robust plan. Let me unpack this, and it's worth noting the rest.")
        assert {"banned:robust", "banned:unpack this", "banned:it's worth noting"} <= set(out)

    def test_clean_prose_has_no_banned_flag(self) -> None:
        assert not [f for f in flags("A plain plan that works.") if f.startswith("banned:")]

    def test_banned_words_in_code_are_ignored(self) -> None:
        assert not [f for f in flags("Set `robust=True`.\n```\nleverage()\n```") if f.startswith("banned:")]

    @pytest.mark.parametrize("claim", ["I tried everything.", "Checked every table.",
                                       "Scanned all tables.", "Ran all notebooks."])
    def test_sweeping_claims_are_flagged(self, claim: str) -> None:
        assert "sweeping" in flags(claim)

    @pytest.mark.parametrize("text", ["Checked each table by name.", "Add every tablespoon."])
    def test_scoped_claims_are_not_sweeping(self, text: str) -> None:
        assert "sweeping" not in flags(text)


class TestNumbers:
    def test_numbers_with_no_tool_call_are_flagged(self) -> None:
        assert "unsourced-numbers" in flags("Model 0.71 against baseline 0.64.", NO_TOOLS)

    def test_numbers_after_a_tool_call_pass(self) -> None:
        assert "unsourced-numbers" not in flags("Model 0.71 against baseline 0.64.", WITH_TOOLS)

    def test_one_number_is_not_enough(self) -> None:
        assert "unsourced-numbers" not in flags("It took 3 tries.", NO_TOOLS)

    def test_dates_times_versions_hashes_and_refs_are_not_quantities(self) -> None:
        reply = ("Shipped 2026-09-24 at 14:30, due 1 October and Jan 2027, on v2.1.233 and 3.4.5, "
                 "commit 3f9c2ab, see reply_check.py:120-145, the 3rd try.")
        assert hook.count_numbers(reply) == 0
        assert "unsourced-numbers" not in flags(reply, NO_TOOLS)

    def test_list_markers_and_code_are_not_quantities(self) -> None:
        reply = "1. first step\n2) second step\nThen `0.71` and\n```\n0.64 12\n```"
        assert "unsourced-numbers" not in flags(reply, NO_TOOLS)

    def test_units_ratios_and_money_count_once_each(self) -> None:
        assert hook.count_numbers("150ms, 4MB, 18/24 and $5") == 4

    def test_month_words_inside_other_words_are_not_dates(self) -> None:
        assert hook.count_numbers("3 decisions and 5 markets") == 2

    def test_an_unreadable_transcript_skips_the_transcript_checks(self) -> None:
        out = hook.measure("Model 0.71 against baseline 0.64.", None)
        assert out["tools"] is None and "unsourced-numbers" not in out["flags"]


class TestDiagnosis:
    def test_edits_on_a_fix_prompt_without_a_diagnosis_are_flagged(self) -> None:
        assert "no-diagnosis" in flags("Done.", FIX)

    def test_a_diagnosis_in_the_turn_or_the_reply_clears_it(self) -> None:
        assert "no-diagnosis" not in flags("Done.", hook.Turn(FIX.prompt, FIX.tools, True))
        assert "no-diagnosis" not in flags("<diagnosis>\nProblem: x\n</diagnosis>\nDone.", FIX)

    @pytest.mark.parametrize("prompt", ["it doesn't work", "the job isn’t working", "tests are failing",
                                        "there's a bug", "this errors out"])
    def test_fix_it_wording_is_recognised(self, prompt: str) -> None:
        assert "no-diagnosis" in flags("Done.", hook.Turn(prompt, ("Write",), False))

    @pytest.mark.parametrize("turn", [
        pytest.param(hook.Turn("add a chart", ("Edit",), False), id="not a fix-it prompt"),
        pytest.param(hook.Turn("fix the crash", ("Read", "Bash"), False), id="no edits"),
        pytest.param(hook.Turn("pull the latest fixtures", ("Edit",), False), id="freight fixtures"),
    ])
    def test_no_diagnosis_needs_a_fix_prompt_and_an_edit(self, turn: hook.Turn) -> None:
        assert "no-diagnosis" not in flags("Done.", turn)

    def test_notebook_edits_count(self) -> None:
        assert "no-diagnosis" in flags("Done.", hook.Turn("fix the error", ("NotebookEdit",), False))


class TestTranscript:
    def test_the_turn_starts_at_the_last_human_prompt(self, tmp_path: Path) -> None:
        path = transcript(tmp_path, [
            human("first ask"), called("Edit"), said("<diagnosis>old</diagnosis>"),
            human("fix the loader bug"), called("Read"), result('{"origin":{"kind":"human"}} "tool_use"'),
            notification("<task-notification>done</task-notification>"),
            called("Write", sidechain=True), called("Edit"), said("Fixed."),
        ])
        assert hook.load_turn(path) == hook.Turn("fix the loader bug", ("Read", "Edit"), False)

    def test_a_diagnosis_in_the_turn_is_found(self, tmp_path: Path) -> None:
        path = transcript(tmp_path, [human("fix it"), said("<diagnosis>\nProblem: x\n</diagnosis>"),
                                     called("Edit")])
        assert hook.load_turn(path).diagnosed

    def test_only_the_tail_is_read(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        pad = [said("x" * 200)] * 50
        monkeypatch.setattr(hook, "TRANSCRIPT_TAIL", 1000)
        near = transcript(tmp_path, [human("old ask"), *pad, human("new ask"), called("Read")], "near.jsonl")
        assert hook.load_turn(near) == hook.Turn("new ask", ("Read",), False)
        far = transcript(tmp_path, [human("old ask"), called("Bash"), *pad, called("Read")], "far.jsonl")
        assert hook.load_turn(far) == hook.Turn("", ("Read",), False)
        assert all(json.loads(raw) for raw in hook.read_tail(far, 1000) if raw)

    def test_spaced_json_is_parsed_too(self, tmp_path: Path) -> None:
        path = tmp_path / "spaced.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in [human("fix it"), called("Edit")]), encoding="utf-8")
        assert hook.load_turn(path) == hook.Turn("fix it", ("Edit",), False)

    def test_last_prompt_is_the_latest_human_row(self, tmp_path: Path) -> None:
        path = transcript(tmp_path, [human("one"), said("a"), human("two"), notification("three")])
        assert hook.last_prompt(path) == "two"


class TestLog:
    def test_the_record_has_the_agreed_shape_and_no_reply_text(self, tmp_path: Path) -> None:
        path = transcript(tmp_path, [human("how did the model do?")])
        reply = "Model 0.71 against baseline 0.64 — close.\n| a | b |\n|---|---|"
        out = run("reply_check.py", stop_payload(path, reply), CLAUDE_CONFIG_DIR=str(tmp_path))
        assert (out.returncode, out.stdout) == (0, b"")
        raw = (tmp_path / "state" / "reply_check.jsonl").read_text(encoding="utf-8")
        rec = json.loads(raw)
        assert list(rec) == ["ts", "session", "lines", "words", "tools", "flags"]
        assert rec["ts"].endswith("Z") and datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))
        assert {k: rec[k] for k in list(rec)[1:]} == {"session": "s1", "lines": 3, "words": 8, "tools": 0,
                                                      "flags": ["table", "unsourced-numbers"]}
        assert "0.71" not in raw and "Model" not in raw

    def test_one_line_per_reply(self, tmp_path: Path) -> None:
        path = transcript(tmp_path, [human("hi"), called("Read")])
        for _ in range(2):
            run("reply_check.py", stop_payload(path, "Done."), CLAUDE_CONFIG_DIR=str(tmp_path))
        logged = (tmp_path / "state" / "reply_check.jsonl").read_text(encoding="utf-8").splitlines()
        assert [json.loads(x)["flags"] for x in logged] == [[], []]

    def test_bad_input_never_blocks_or_logs(self, tmp_path: Path) -> None:
        out = run("reply_check.py", b"not json", CLAUDE_CONFIG_DIR=str(tmp_path))
        assert (out.returncode, out.stdout) == (0, b"")
        assert out.stderr.startswith(b"reply_check: ")
        assert not (tmp_path / "state").exists()

    def test_a_missing_transcript_logs_null_tools(self, tmp_path: Path) -> None:
        out = run("reply_check.py", stop_payload(tmp_path / "gone.jsonl", "Done."), CLAUDE_CONFIG_DIR=str(tmp_path))
        rec = json.loads((tmp_path / "state" / "reply_check.jsonl").read_text(encoding="utf-8"))
        assert out.returncode == 0 and rec["tools"] is None and rec["flags"] == []

    def test_the_escape_hatch_writes_nothing(self, tmp_path: Path) -> None:
        path = transcript(tmp_path, [human("hi")])
        out = run("reply_check.py", stop_payload(path, "Done."), CLAUDE_CONFIG_DIR=str(tmp_path),
                  CLAUDE_REPLY_CHECK="off")
        assert out.returncode == 0 and not (tmp_path / "state").exists()

    def test_a_broken_git_guard_costs_only_the_banned_word_check(self, tmp_path: Path) -> None:
        hooks = tmp_path / "hooks"
        hooks.mkdir()
        (hooks / "reply_check.py").write_bytes((HOOKS / "reply_check.py").read_bytes())
        (hooks / "git_guard.py").write_text("BANNED_TERMS = None\n", encoding="utf-8")
        path = transcript(tmp_path, [human("hi"), called("Read")])
        out = run(str(hooks / "reply_check.py"), stop_payload(path, "Let me delve.\n| a | b |\n|---|---|"),
                  CLAUDE_CONFIG_DIR=str(tmp_path))
        assert (out.returncode, out.stdout) == (0, b"")
        rec = json.loads((tmp_path / "state" / "reply_check.jsonl").read_text(encoding="utf-8"))
        assert rec["flags"] == ["table"]


class TestFeedback:
    def voice(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, stdin: bytes) -> dict:
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
        assert human_voice.main() == 0
        return json.loads(capsys.readouterr().out)

    def context(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, session: str) -> str:
        payload = json.dumps({"session_id": session, "prompt": "hi"}).encode()
        return self.voice(monkeypatch, capsys, payload)["hookSpecificOutput"]["additionalContext"]

    def test_describe_names_each_flag_in_plain_words(self) -> None:
        assert hook.describe(record("s1", ["long", "table", "unsourced-numbers"], lines_=14)) == EXAMPLE

    def test_describe_covers_word_counts_and_banned_words(self) -> None:
        rec = record("s1", ["long", "banned:delve", "banned:robust"], lines_=4, words=300)
        assert hook.describe(rec) == "Your last reply was flagged: 300 words (limit 220), banned words (delve, robust)."
        assert hook.describe(record("s1", [])) == ""

    def test_every_flag_has_words(self) -> None:
        for flag in ("table", "bullets", "sweeping", "unsourced-numbers", "no-diagnosis", "banned:delve"):
            assert hook.describe(record("s1", [flag])).startswith("Your last reply was flagged: ")

    def test_a_flagged_reply_adds_one_sentence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                               capsys: pytest.CaptureFixture) -> None:
        log = write_log(tmp_path / "log.jsonl", record("s1", ["long", "table", "unsourced-numbers"], lines_=14),
                        record("s2", []))
        monkeypatch.setattr(hook, "LOG", log)
        payload = json.dumps({"session_id": "s1", "prompt": "hi"}).encode()
        assert self.voice(monkeypatch, capsys, payload) == {
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                   "additionalContext": f"{human_voice.RULE}\n{EXAMPLE}"},
            "suppressOutput": True,
        }

    def test_a_clean_last_reply_leaves_the_rule_alone(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                      capsys: pytest.CaptureFixture) -> None:
        log = write_log(tmp_path / "log.jsonl", record("s1", ["table"]), record("s1", []), record("s2", ["table"]))
        monkeypatch.setattr(hook, "LOG", log)
        assert self.context(monkeypatch, capsys, "s1") == human_voice.RULE
        assert self.context(monkeypatch, capsys, "s3") == human_voice.RULE

    def test_no_log_bad_stdin_or_escape_hatch_leave_the_rule_alone(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
        monkeypatch.setattr(hook, "LOG", tmp_path / "missing.jsonl")
        assert self.context(monkeypatch, capsys, "s1") == human_voice.RULE
        monkeypatch.setattr(hook, "LOG", write_log(tmp_path / "log.jsonl", record("s1", ["table"])))
        assert self.voice(monkeypatch, capsys, b"")["hookSpecificOutput"]["additionalContext"] == human_voice.RULE
        monkeypatch.setenv("CLAUDE_REPLY_CHECK", "off")
        assert self.context(monkeypatch, capsys, "s1") == human_voice.RULE

    def test_only_the_log_tail_is_read(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        log = write_log(tmp_path / "log.jsonl", record("old", ["table"]), *[record("s2", [])] * 50,
                        record("s1", ["table"]))
        monkeypatch.setattr(hook, "LOG", log)
        monkeypatch.setattr(hook, "LOG_TAIL", 1000)
        assert hook.feedback("s1") == "Your last reply was flagged: a table."
        assert hook.feedback("old") == ""

    def test_human_voice_runs_as_a_script_with_the_sentence(self, tmp_path: Path) -> None:
        write_log(tmp_path / "state" / "reply_check.jsonl", record("s1", ["bullets"]))
        out = run("human_voice.py", {"session_id": "s1", "prompt": "hi"}, CLAUDE_CONFIG_DIR=str(tmp_path))
        context = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
        assert context == f"{human_voice.RULE}\nYour last reply was flagged: a bullet wall (6+ list lines in a row)."
