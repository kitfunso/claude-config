#!/usr/bin/env python3
"""PreToolUse hook (Edit/Write): backstop for the reuse rule (karpathy-guidelines rung 2).

A Write or Edit that adds a function or class whose name the repo already defines in another
file of the same language is denied once per session, naming each existing definition; the
same write again passes. A new code file with no clash gets a one-line reuse reminder, and a
new .html report gets the report rule, each once per session. Logs to
~/.claude/state/reuse_guard.jsonl. Escape hatch: CLAUDE_REUSE_GUARD=off. On any error the
call is allowed and one stderr line names the error; a broken guard must not break the session.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
try:
    from record_component import record
except Exception:  # the recorder is optional, the deny is not
    def record(**_: object) -> None:
        return None

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
LOG = CLAUDE_DIR / "state" / "reuse_guard.jsonl"
PY = re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+(\w+)|^[ \t]*class[ \t]+(\w+)", re.M)
JS = re.compile(
    r"\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)\s*\("
    r"|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)"
    r"|^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)", re.M)
FAMILY = {".py": PY, ".js": JS, ".mjs": JS, ".cjs": JS, ".jsx": JS, ".ts": JS, ".tsx": JS}
MARKERS = (".git", "pyproject.toml", "package.json", "setup.py", "setup.cfg", "go.mod", "Cargo.toml")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next",
             ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "site-packages", "coverage", "target"}
# Entry points and plumbing every script has; a clash on these says nothing about reuse.
STOP = {"main", "run", "decide", "setup", "teardown", "handler", "handle", "wrapper", "inner",
        "callback", "default", "init", "start", "stop", "close", "open", "index", "cli", "app",
        "parse_args", "configure", "register", "Config", "Settings", "Meta", "render", "build",
        "load", "save", "write", "read", "compute", "parse", "label", "name", "table", "cell",
        "frame", "span", "years", "score", "report", "inputs", "header", "footer", "update",
        "create", "process", "generate", "health"}
TEST = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.py$|\.(test|spec)\.[jt]sx?$")
MAX_FILES, MAX_BYTES, BUDGET_S, SHOWN, CONVENTION = 5000, 512_000, 4.0, 8, 4
DENY = (
    "[REUSE GUARD] {path} adds {what} this repo already defines: {hits}. Reuse rule "
    "(karpathy-guidelines rung 2): import or adapt the existing code instead of writing a "
    "parallel version. If it truly cannot fit, tell Keith in one line in chat why, then make "
    "the same write again; it passes the second time. Escape hatch: CLAUDE_REUSE_GUARD=off."
)
CODE_NOTE = (
    "[REUSE] New code file {path}. Before writing more: search this repo for the functions, "
    "tables and pages you need and import them. If an existing one cannot fit, say why in "
    "chat before writing a parallel version."
)
HTML_NOTE = (
    "[REPORT] New report {path}. Every number in a headline must come from values computed "
    "in this run, asserted in the code that renders it; render it through the project's "
    "existing page code if it has one; show every cell Keith asked to judge, and name in "
    "chat anything left out."
)


def name_of(m: re.Match) -> str | None:
    return next((g for g in m.groups() if g), None)


def names_in(text: str, pattern: re.Pattern) -> set[str]:
    found = {name_of(m) for m in pattern.finditer(text)}
    return {n for n in found if n and len(n) >= 4 and n not in STOP
            and not n.startswith(("test", "Test", "__"))}


def added_names(payload: dict, target: Path, pattern: re.Pattern) -> set[str]:
    """Names this call adds: all of a new file, else those absent from the text it replaces."""
    inp = payload.get("tool_input") or {}
    if payload.get("tool_name") == "Write":
        before = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else ""
        return names_in(inp.get("content") or "", pattern) - names_in(before, pattern)
    edits = inp.get("edits") or [inp]
    new = set().union(*(names_in(e.get("new_string") or "", pattern) for e in edits))
    old = set().union(*(names_in(e.get("old_string") or "", pattern) for e in edits))
    return new - old


def repo_root(target: Path, cwd: str | None) -> Path:
    home = Path.home().resolve()
    for d in target.parents:
        if d == home or d == d.parent:
            break
        if any((d / m).exists() for m in MARKERS):
            return d
    here = Path(cwd).resolve() if cwd else None
    if here and here != home and here in target.parents:
        return here
    return target.parent


def candidates(root: Path, exts: set[str]):
    """Code files under root: git's list where there is one, so ignored data stays out."""
    if (root / ".git").exists():
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"],
                             capture_output=True, text=True, encoding="utf-8", timeout=5)
        if out.returncode == 0:
            yield from (root / f for f in out.stdout.splitlines()
                        if Path(f).suffix in exts and not SKIP_DIRS.intersection(Path(f).parts))
            return
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        yield from (Path(d) / f for f in fs if Path(f).suffix in exts)


def is_test(path: str) -> bool:
    return bool(TEST.search(path.replace("\\", "/")))


def existing(root: Path, target: Path, names: set[str], pattern: re.Pattern) -> list[str]:
    """`name (file:line)` for each name another non-test file of the same family defines; a
    name defined in CONVENTION or more files is a convention and passes."""
    exts = {e for e, p in FAMILY.items() if p is pattern}
    where: dict[str, dict[str, int]] = {}
    until = time.monotonic() + BUDGET_S
    for i, p in enumerate(candidates(root, exts)):
        rel = p.relative_to(root).as_posix()
        if i >= MAX_FILES or time.monotonic() > until:
            break
        try:
            if is_test(rel) or p.resolve() == target or p.stat().st_size > MAX_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in pattern.finditer(text):
            n = name_of(m)
            if n in names:
                where.setdefault(n, {}).setdefault(rel, text.count("\n", 0, m.start()) + 1)
    return [f"{n} ({', '.join(f'{f}:{line}' for f, line in at.items())})"
            for n, at in sorted(where.items()) if len(at) < CONVENTION]


def logged(session: str | None, key: str) -> bool:
    if not LOG.is_file():
        return False
    for raw in LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]:
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if row.get("session") == session and row.get("key") == key:
            return True
    return False


def log(session: str | None, key: str, action: str, detail: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": stamp, "session": session, "key": key, "action": action,
                             "detail": detail}) + "\n")


def note(session: str | None, key: str, text: str) -> dict | None:
    if logged(session, key):
        return None
    log(session, key, "remind", text)
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}


def decide(payload: dict) -> dict | None:
    """A deny for a clashing write, a reminder for a new file, else None."""
    if payload.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return None
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        return None
    target, session = Path(file_path).resolve(), payload.get("session_id")
    new = payload.get("tool_name") == "Write" and not target.exists()
    if target.suffix.lower() in (".html", ".htm"):
        return note(session, f"html|{target}", HTML_NOTE.format(path=target)) if new else None
    pattern = FAMILY.get(target.suffix.lower())
    if pattern is None:
        return None
    root = repo_root(target, payload.get("cwd"))
    test = is_test(target.relative_to(root).as_posix())
    names = set() if test else added_names(payload, target, pattern)
    hits = existing(root, target, names, pattern) if names else []
    if not hits:
        return note(session, f"code|{root}", CODE_NOTE.format(path=target)) if new else None
    key = f"deny|{target}|{','.join(sorted(h.split(' ')[0] for h in hits))}"
    if logged(session, key):
        log(session, key, "pass", "second try")
        return None
    what = f"{len(hits)} name{'s' if len(hits) != 1 else ''}"
    reason = DENY.format(path=target, what=what, hits="; ".join(hits[:SHOWN]))
    log(session, key, "deny", reason)
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def main() -> None:
    if os.environ.get("CLAUDE_REUSE_GUARD", "").lower() == "off":
        return
    payload = json.loads(sys.stdin.buffer.read())
    out = decide(payload)
    if out:
        spec = out["hookSpecificOutput"]
        if spec.get("permissionDecision") == "deny":
            record(kind="hook", name=Path(__file__).name, session_id=payload.get("session_id"),
                   cwd=payload.get("cwd"), blocked=True, notes=spec["permissionDecisionReason"])
        json.dump(out, sys.stdout)


if __name__ == "__main__":
    logging.basicConfig(format="%(name)s: %(message)s")
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - a guard must never break the session
        logging.getLogger("reuse_guard").error("%s: %s", type(exc).__name__, exc)
    sys.exit(0)
