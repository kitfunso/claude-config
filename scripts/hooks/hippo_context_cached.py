#!/usr/bin/env python3
"""Serve hippo's pinned-memory injection from a cache, refreshed out of band.

`hippo context` costs 0.57s idle but 28-57s under 24-core load, against a 15s
hook budget, so the injection was dropped whenever the box was busy.
See docs/incidents.md (2026-09-06).
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

ARGS = ["context", "--pinned-only", "--include-recent", "5",
        "--format", "additional-context"]
CACHE_DIR = (Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
             / "cache" / "hippo-context")
LOCK_TTL = 300.0
COLD_TIMEOUT = 12.0


def hippo() -> str | None:
    return shutil.which("hippo")


def cache_file(cwd: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha1(cwd.encode('utf-8')).hexdigest()[:16]}.json"


def run_hippo(cwd: str, timeout: float) -> str | None:
    exe = hippo()
    if not exe:
        return None
    try:
        done = subprocess.run([exe, *ARGS], cwd=cwd, capture_output=True,
                              timeout=timeout, text=True, encoding="utf-8")
    except (OSError, subprocess.SubprocessError):
        return None
    out = (done.stdout or "").strip()
    return out if done.returncode == 0 and out else None


def write_cache(path: Path, payload: str) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def refresh_running(lock: Path) -> bool:
    """A crashed refresh must not wedge the cache, so the lock expires."""
    try:
        return time.time() - lock.stat().st_mtime < LOCK_TTL
    except OSError:
        return False


def spawn_refresh(cwd: str) -> None:
    lock = cache_file(cwd).with_suffix(".lock")
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
        path.with_suffix(".lock").unlink()
    except OSError:
        pass
    return 0


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--refresh":
        return refresh(sys.argv[2])

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    cwd = payload.get("cwd") or os.getcwd()

    cached = None
    try:
        cached = cache_file(cwd).read_text(encoding="utf-8")
    except OSError:
        pass

    if cached:
        print(cached)
        spawn_refresh(cwd)
        return 0

    out = run_hippo(cwd, timeout=COLD_TIMEOUT)
    if out:
        write_cache(cache_file(cwd), out)
        print(out)
    else:
        spawn_refresh(cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
