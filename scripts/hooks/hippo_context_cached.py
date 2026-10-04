#!/usr/bin/env python3
"""Serve hippo's pinned rules from a cache and add hippo's live prompt recall.

`hippo context` costs 1-4s idle but 28-57s under 24-core load, against a 15s hook
budget. See docs/incidents.md (2026-09-06, 2026-09-13, and 2026-10-04 for recall).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Pinned rules only: the last-N-writes add-on was global, so every prompt carried other projects' notes.
ARGS = ["context", "--pinned-only", "--format", "additional-context"]
CACHE_DIR = (Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
             / "cache" / "hippo-context")
LOCK_TTL = 60.0
COLD_TIMEOUT = 12.0
HOOK_BUDGET = 13.0
RECALL_TIMEOUT = 4.0
RECALL_BACKOFF = 300.0
MEMORY_HEADING = "## Project Memory"
RECALL_HEADING = "## Prompt-Relevant Memory"


def hippo() -> str | None:
    return shutil.which("hippo")


def cache_file(cwd: str) -> Path:
    """One key per folder and query: slash style never splits it, and a changed query never serves the old cache."""
    key = "\0".join([cwd.replace("\\", "/").rstrip("/"), *ARGS])
    return CACHE_DIR / f"{hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]}.json"


def lock_file() -> Path:
    """One lock for the whole store: two concurrent refreshes deadlock SQLite."""
    return CACHE_DIR / "refresh.lock"


def strip_snapshot(payload: str) -> str:
    """The SessionStart hook already prints the snapshot; per prompt it is dead weight."""
    try:
        doc = json.loads(payload)
        block = doc["hookSpecificOutput"]["additionalContext"]
        cut = block.find(MEMORY_HEADING)
    except (ValueError, KeyError, TypeError, AttributeError):
        return payload
    if cut <= 0:
        return payload
    doc["hookSpecificOutput"]["additionalContext"] = block[cut:]
    return json.dumps(doc)


def exec_hippo(cwd: str, timeout: float, stdin_text: str | None = None) -> str | None:
    exe = hippo()
    if not exe:
        return None
    done = subprocess.run([exe, *ARGS], cwd=cwd, capture_output=True, input=stdin_text,
                          timeout=timeout, text=True, encoding="utf-8",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    out = (done.stdout or "").strip()
    return out if done.returncode == 0 and out else None


def run_hippo(cwd: str, timeout: float) -> str | None:
    try:
        out = exec_hippo(cwd, timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return strip_snapshot(out) if out else None


def context_text(raw: str | None) -> str:
    try:
        text = json.loads(raw or "")["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError):
        return ""
    return text if isinstance(text, str) else ""


def recall_section(raw: str | None) -> str:
    text = context_text(raw)
    cut = text.find(RECALL_HEADING)
    return text[cut:].strip() if cut >= 0 else ""


def backoff_file() -> Path:
    return CACHE_DIR / "recall.slow"


def prompt_recall(cwd: str, stdin_text: str, prompt: str, timeout: float) -> str:
    """The cache cannot match a prompt, so recall runs live; a timeout pauses it so a busy box stays fast."""
    if not prompt.strip() or timeout < 1.0 or os.environ.get("CLAUDE_HIPPO_RECALL", "").lower() == "off":
        return ""
    try:
        if time.time() - backoff_file().stat().st_mtime < RECALL_BACKOFF:
            return ""
    except OSError:
        pass
    try:
        return recall_section(exec_hippo(cwd, timeout, stdin_text))
    except subprocess.TimeoutExpired:
        write_cache(backoff_file(), str(time.time()))
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def merge(static: str | None, recall: str) -> str | None:
    """Pinned rules go once per session, recall goes every prompt, so they travel as one block."""
    if not recall:
        return static
    text = context_text(static)
    joined = f"{text}\n\n{recall}" if text else recall
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": joined}})


def write_cache(path: Path, payload: str) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


# SHORTCUT: markers are never deleted (40 bytes a session); sweep by mtime if the dir grows.
def seen_file(session_id: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha1(session_id.encode('utf-8')).hexdigest()[:16]}.seen"


def already_sent(session_id: str, out: str) -> bool:
    """The block stays in context until a compaction, so a repeat only burns tokens."""
    if not session_id or os.environ.get("CLAUDE_HIPPO_DEDUPE", "").lower() == "off":
        return False
    path = seen_file(session_id)
    try:
        seen = path.read_text(encoding="utf-8")
    except OSError:
        # no marker: this box has no --reset hook, so nothing would re-send after a compaction
        return False
    digest = hashlib.sha1(out.encode("utf-8")).hexdigest()
    if seen == digest:
        return True
    write_cache(path, digest)
    return False


def reset(session_id: str) -> int:
    """SessionStart runs this: a compaction or /clear drops the block, so arm one fresh send."""
    if session_id:
        write_cache(seen_file(session_id), "")
    return 0


def refresh_running(lock: Path) -> bool:
    """A crashed refresh must not wedge the cache, so the lock expires."""
    try:
        return time.time() - lock.stat().st_mtime < LOCK_TTL
    except OSError:
        return False


def spawn_refresh(cwd: str) -> None:
    lock = lock_file()
    if refresh_running(lock):
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        lock.write_text(str(os.getpid()), encoding="utf-8")
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--refresh", cwd],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True, creationflags=flags,
        )
    except OSError:
        try:
            lock.unlink()
        except OSError:
            pass


def refresh(cwd: str) -> int:
    path = cache_file(cwd)
    out = run_hippo(cwd, timeout=600.0)
    if out:
        write_cache(path, out)
    try:
        lock_file().unlink()
    except OSError:
        pass
    return 0


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--refresh":
        return refresh(sys.argv[2])

    started = time.monotonic()
    raw = sys.stdin.read() or "{}"
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    session_id = payload.get("session_id") or ""
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        return reset(session_id)
    cwd = payload.get("cwd") or os.getcwd()

    static = None
    try:
        static = cache_file(cwd).read_text(encoding="utf-8")
    except OSError:
        pass
    if static:
        spawn_refresh(cwd)
    else:
        static = run_hippo(cwd, timeout=COLD_TIMEOUT)
        if static:
            write_cache(cache_file(cwd), static)
        else:
            spawn_refresh(cwd)

    unsent = static if static and not already_sent(session_id, static) else None
    prompt = payload.get("prompt")
    remaining = HOOK_BUDGET - (time.monotonic() - started)
    recall = prompt_recall(cwd, raw, prompt if isinstance(prompt, str) else "",
                           min(RECALL_TIMEOUT, remaining))
    out = merge(unsent, recall)
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
