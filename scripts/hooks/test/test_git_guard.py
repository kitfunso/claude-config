"""Tests for git_guard.resolve_dir, the path the branch note reads.

Run: python -m pytest scripts/hooks/test -q -p no:cacheprovider
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

import git_guard  # noqa: E402


def test_tilde_expands_to_home() -> None:
    assert git_guard.resolve_dir("~/.claude", "C:/elsewhere") == os.path.expanduser("~/.claude")


def test_git_bash_drive_path_becomes_windows() -> None:
    assert git_guard.resolve_dir("/c/Users/kit/dev", None) == "C:/Users/kit/dev"


def test_variable_path_falls_back_to_cwd() -> None:
    assert git_guard.resolve_dir("$HOME/.claude", "C:/work") == "C:/work"


def test_no_path_falls_back_to_cwd_then_dot() -> None:
    assert git_guard.resolve_dir(None, "C:/work") == "C:/work"
    assert git_guard.resolve_dir(None, None) == "."


def test_tilde_command_reads_the_real_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (["init", "-q", "-b", "main"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    assert git_guard.current_branch(git_guard.resolve_dir("~/repo", None)) == "main"
