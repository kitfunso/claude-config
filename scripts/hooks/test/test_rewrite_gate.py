"""Tests for the rewrite gate: a full Write over a hand-maintained file waits for "apply".

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

import rewrite_gate as gate  # noqa: E402

DENY_KEYS = {"hookEventName", "permissionDecision", "permissionDecisionReason"}


def human(text: str, **extra: object) -> dict:
    return {"type": "user", "isSidechain": False, "origin": {"kind": "human"},
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}, **extra}


def transcript(tmp_path: Path, *rows: dict) -> Path:
    path = tmp_path / "session.jsonl"
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    return path


def write(target: Path, transcript_path: Path | None, tool: str = "Write") -> dict:
    return {"session_id": "s1", "transcript_path": str(transcript_path) if transcript_path else None,
            "cwd": str(target.parent), "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {"file_path": str(target), "content": "new\n"}}


def reason(out: dict | None) -> str:
    assert out is not None
    return out["hookSpecificOutput"]["permissionDecisionReason"]


def run(payload: object, script: Path = HOOKS / "rewrite_gate.py", **env: str) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.run([sys.executable, str(script)], input=data, capture_output=True,
                          env={**os.environ, "CLAUDE_REWRITE_GATE": "", **env}, timeout=30)


@pytest.fixture
def claude_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git checkout standing in for ~/.claude: rules/tracked.md is tracked, notes.md is not."""
    repo = tmp_path / "claude"
    (repo / "rules").mkdir(parents=True)
    for name in ("rules/tracked.md", "notes.md"):
        (repo / name).write_text("old\n", encoding="utf-8")
    for args in (["init", "-q"], ["add", "rules/tracked.md"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    monkeypatch.setattr(gate, "CLAUDE_DIR", repo)
    return repo


@pytest.fixture
def tracked(claude_dir: Path) -> Path:
    return claude_dir / "rules" / "tracked.md"


def test_a_tracked_file_is_denied_without_apply(tmp_path: Path, tracked: Path) -> None:
    out = gate.decide(write(tracked, transcript(tmp_path, human("tidy the rules"))))
    assert out is not None and set(out) == {"hookSpecificOutput"}
    assert set(out["hookSpecificOutput"]) == DENY_KEYS
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    text = reason(out)
    assert "tracked.md" in text and '"apply"' in text and "targeted Edits" in text


@pytest.mark.parametrize("prompt", ["apply", "Apply.", "ok, apply consolidated fixes"])
def test_apply_in_the_latest_prompt_allows(tmp_path: Path, tracked: Path, prompt: str) -> None:
    assert gate.decide(write(tracked, transcript(tmp_path, human(prompt)))) is None


@pytest.mark.parametrize("prompt", ["applying it later", "already applied", "reapply the patch"])
def test_apply_must_be_the_whole_word(tmp_path: Path, tracked: Path, prompt: str) -> None:
    assert gate.decide(write(tracked, transcript(tmp_path, human(prompt)))) is not None


def test_only_the_latest_human_prompt_counts(tmp_path: Path, tracked: Path) -> None:
    notice = {"type": "user", "isSidechain": False, "origin": {"kind": "task-notification"},
              "message": {"role": "user", "content": "apply"}}
    path = transcript(tmp_path, human("apply"), human("now rewrite it"), notice, human("apply", isSidechain=True))
    assert gate.decide(write(tracked, path)) is not None


def test_untracked_and_new_files_pass(tmp_path: Path, claude_dir: Path) -> None:
    path = transcript(tmp_path, human("rewrite them"))
    for target in (claude_dir / "notes.md", claude_dir / "rules" / "new.md", tmp_path / "fresh" / "CLAUDE.md"):
        assert gate.decide(write(target, path)) is None


def test_claude_md_is_gated_anywhere(tmp_path: Path, claude_dir: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text("old\n", encoding="utf-8")
    path = transcript(tmp_path, human("rewrite the project rules"))
    assert "CLAUDE.md" in reason(gate.decide(write(project / "CLAUDE.md", path)))
    assert gate.decide(write(project / "CLAUDE.md", transcript(tmp_path, human("apply")))) is None


def test_settings_json_is_gated_though_git_never_tracks_it(tmp_path: Path, claude_dir: Path) -> None:
    settings = claude_dir / "settings.json"
    settings.write_text("{}\n", encoding="utf-8")
    assert gate.decide(write(settings, transcript(tmp_path, human("add a hook")))) is not None
    assert gate.decide(write(settings, transcript(tmp_path, human("apply")))) is None


def test_edits_are_never_gated(tmp_path: Path, tracked: Path) -> None:
    assert gate.decide(write(tracked, transcript(tmp_path, human("tidy")), tool="Edit")) is None


def test_a_failing_git_reads_as_untracked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "rules.md").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(gate, "CLAUDE_DIR", plain)
    assert gate.decide(write(plain / "rules.md", transcript(tmp_path, human("rewrite")))) is None


def test_the_script_denies_with_the_hook_json(tmp_path: Path, claude_dir: Path, tracked: Path) -> None:
    out = run(write(tracked, transcript(tmp_path, human("tidy"))),
              CLAUDE_CONFIG_DIR=str(claude_dir), DEVRL_DB=str(tmp_path / "none.db"))
    assert out.returncode == 0
    assert json.loads(out.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_the_script_allows_after_apply(tmp_path: Path, claude_dir: Path, tracked: Path) -> None:
    out = run(write(tracked, transcript(tmp_path, human("apply"))), CLAUDE_CONFIG_DIR=str(claude_dir))
    assert (out.returncode, out.stdout) == (0, b"")


def test_a_broken_git_guard_keeps_the_gate_shut(tmp_path: Path, claude_dir: Path, tracked: Path) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    for name in ("rewrite_gate.py", "reply_check.py"):
        (hooks / name).write_bytes((HOOKS / name).read_bytes())
    (hooks / "git_guard.py").write_text("BANNED_TERMS = None\n", encoding="utf-8")
    out = run(write(tracked, transcript(tmp_path, human("tidy"))), script=hooks / "rewrite_gate.py",
              CLAUDE_CONFIG_DIR=str(claude_dir))
    assert out.returncode == 0
    assert json.loads(out.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_the_escape_hatch_allows(tmp_path: Path, claude_dir: Path, tracked: Path) -> None:
    out = run(write(tracked, transcript(tmp_path, human("tidy"))), CLAUDE_CONFIG_DIR=str(claude_dir),
              CLAUDE_REWRITE_GATE="off")
    assert (out.returncode, out.stdout) == (0, b"")


@pytest.mark.parametrize("broken", ["not json", "no transcript", "missing transcript file"])
def test_errors_allow_silently(tmp_path: Path, claude_dir: Path, tracked: Path, broken: str) -> None:
    payload = {"not json": b"{oops", "no transcript": write(tracked, None),
               "missing transcript file": write(tracked, tmp_path / "gone.jsonl")}[broken]
    out = run(payload, CLAUDE_CONFIG_DIR=str(claude_dir), DEVRL_DB=str(tmp_path / "none.db"))
    assert (out.returncode, out.stdout) == (0, b"")
    assert out.stderr.startswith(b"rewrite_gate: ")
