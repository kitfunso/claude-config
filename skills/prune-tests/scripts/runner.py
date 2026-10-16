"""Shared helpers for prune-tests: run pytest with the plugin, read its log, guard worktrees."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
OMIT = "*test_*.py,*_test.py,*conftest.py,*/tests/*,*/site-packages/*,.venv/*"


@dataclass(frozen=True)
class Run:
    rc: int
    seconds: float
    timed_out: bool
    outcomes: dict = field(default_factory=dict)  # nodeid -> passed|failed|skipped
    durations: dict = field(default_factory=dict)  # nodeid -> seconds, all phases
    collect_errors: tuple = ()

    @property
    def failed(self) -> set:
        return {t for t, o in self.outcomes.items() if o == "failed"}


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, doc: dict) -> None:
    Path(path).write_text(json.dumps(doc, indent=1), encoding="utf-8")


def read_log(path: Path) -> tuple[dict, dict, tuple]:
    phases: dict = {}
    durations: dict = {}
    errors = []
    if not path.exists():
        return {}, durations, ()
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["when"] == "collect":
            errors.append(row["id"])
            continue
        tid = row["id"]
        durations[tid] = durations.get(tid, 0.0) + row["s"]
        phases.setdefault(tid, {})[row["when"]] = row["outcome"]
    # every finished test logs a teardown, so one without it and without a failure was cut off mid-run
    outcomes = {tid: "failed" if "failed" in p.values() else p.get("call", p["setup"])
                for tid, p in phases.items() if "failed" in p.values() or "teardown" in p}
    return outcomes, durations, tuple(errors)


def run_pytest(python: str, repo: Path, args: list[str], *, timeout: float | None = None,
               stop_first: bool = False, coverage_file: Path | None = None) -> Run:
    """Run pytest in repo with the plugin loaded; node ids go through an @argfile."""
    with tempfile.TemporaryDirectory(prefix="prune-") as tmp:
        log = Path(tmp) / "log.jsonl"
        argfile = Path(tmp) / "args.txt"
        argfile.write_text("\n".join(args), encoding="utf-8")
        env = {**_env(), "PRUNE_LOG": str(log),
               "PYTHONPATH": os.pathsep.join(filter(None, [str(SCRIPTS), os.environ.get("PYTHONPATH")]))}
        head = [python, "-m"]
        if coverage_file:
            head += ["coverage", "run", f"--data-file={coverage_file}", "--source=.",
                     f"--omit={OMIT}", "-m"]
        cmd = head + ["pytest", "-q", "-p", "no:cacheprovider", "-p", "prune_plugin",
                      *(["-x"] if stop_first else []), *([f"@{argfile}"] if args else [])]
        start = time.monotonic()
        proc = subprocess.Popen(cmd, cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=os.name != "nt")
        try:
            rc, timed_out = proc.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            rc, timed_out = -1, True
        outcomes, durations, errors = read_log(log)
        return Run(rc, time.monotonic() - start, timed_out, outcomes, durations, errors)


def is_red(run: Run) -> bool:
    """A failure, or a bug that broke collection. A timeout alone proves nothing."""
    return bool(run.failed or run.collect_errors or run.rc in (2, 3, 4))


def red_tests(python: str, repo: Path, run: Run, tests: list[str], timeout_for) -> Iterator[str]:
    """Tests the run shows red. A busy box times batches out too, so an unfinished test counts only alone."""
    yield from sorted(run.failed)
    if run.timed_out:
        for t in tests:
            if t not in run.outcomes:
                alone = run_pytest(python, repo, [t], timeout=timeout_for(t))
                if alone.timed_out or is_red(alone):
                    yield t


def _kill_tree(proc: subprocess.Popen) -> None:
    """A venv python.exe on Windows is a launcher; killing it alone can leave the real run going."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def _env() -> dict:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("VIRTUAL_ENV", None)
    return env


def collect_ids(python: str, repo: Path, args: list[str] = ()) -> list[str]:
    out = subprocess.run([python, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *args],
                         cwd=repo, env=_env(), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [line.strip() for line in out.stdout.splitlines() if "::" in line]


def git(repo: Path, *args: str, check: bool = True) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and out.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def require_scratch_worktree(repo: Path) -> None:
    """Mutation and replay rewrite files; refuse anything but a linked worktree."""
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    own = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-dir").strip())
    if common == own:
        raise SystemExit(f"{repo} is a main checkout; run on a `git worktree add` copy.")
    if git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        raise SystemExit(f"{repo} has uncommitted changes to tracked files.")


def is_test_file(path: str) -> bool:
    p = Path(path)
    return (p.name.startswith("test_") or p.name.endswith("_test.py") or p.name == "conftest.py"
            or bool({"tests", "test"} & set(p.parts[:-1])))
