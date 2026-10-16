"""Past-bug replay: put each recent fix commit's bug back into today's code and see who catches it.

Needs two scratch worktrees with identical source: --base (pre-cut tests) and --slim (post-cut tests).
Verdicts: caught (slim goes red), lost (only a cut test went red), not caught by either, does not apply.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

import runner

FIX = re.compile(r"^fix(\(.+\))?!?:", re.IGNORECASE)
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))?")


def fix_commits(repo: Path, n: int) -> list[tuple[str, str, list[str]]]:
    out = []
    for line in runner.git(repo, "log", "--no-merges", "--format=%H%x09%s", "-n", "2000").splitlines():
        sha, subject = line.split("\t", 1)
        if not FIX.match(subject):
            continue
        files = [f for f in runner.git(repo, "show", "--name-only", "--format=", sha).splitlines()
                 if f.endswith(".py") and not runner.is_test_file(f)]
        if files:
            out.append((sha, subject, files))
        if len(out) == n:
            break
    return out


def head_side_lines(repo: Path) -> dict[str, set[int]]:
    """Lines of HEAD the working-tree change rewrote: the fixed code the bug now replaces."""
    out: dict = {}
    cur = None
    for line in runner.git(repo, "diff", "-U0").splitlines():
        if line.startswith("--- "):
            cur = line[6:] if line.startswith("--- a/") else None
        elif cur and (m := HUNK.match(line)):
            start, count = int(m[1]), int(m[2] if m[2] is not None else 1)
            out.setdefault(cur, set()).update(range(start, start + max(count, 1)))
    return out


def _apply(wt: Path, patch: Path, check: bool) -> bool:
    cmd = ["git", "-C", str(wt), "apply", "-R", "--whitespace=nowarn", *(["--check"] if check else []), str(patch)]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def _restore(wt: Path, files: list[str]) -> None:
    runner.git(wt, "checkout", "--", ".")
    runner.git(wt, "clean", "-fdq", "--", *files)


def _red(run: runner.Run | None) -> bool:
    return bool(run and (run.failed or run.collect_errors or run.timed_out or run.rc in (2, 3)))


def replay_one(sha: str, files: list[str], ctx: dict) -> dict:
    base, slim = ctx["base"], ctx["slim"]
    with tempfile.TemporaryDirectory(prefix="prune-replay-") as tmp:
        patch = Path(tmp) / "fix.patch"
        patch.write_text(runner.git(base, "diff", f"{sha}^", sha, "--", *files), encoding="utf-8")
        if not all(_apply(wt, patch, check=True) for wt in (base, slim)):
            return {"verdict": "does not apply"}
        try:
            for wt in (base, slim):
                _apply(wt, patch, check=False)
            lines = head_side_lines(base)
            covering = {t for f, ls in lines.items() for ln in ls for t in ctx["cover"].get((f, ln), ())}
            cut_cov = sorted(covering & ctx["cut"])
            cut_run = runner.run_pytest(ctx["python"], base, cut_cov, timeout=ctx["budget"]) if cut_cov else None
            cut_files = {t.split("::")[0] for t in cut_cov}
            slim_sel = sorted(t for t in ctx["slim_ids"] if t in covering or t.split("::")[0] in cut_files)
            slim_run = runner.run_pytest(ctx["python"], slim, slim_sel, timeout=ctx["budget"]) if slim_sel else None
        finally:
            for wt in (base, slim):
                _restore(wt, files)
    cut_failed = sorted(cut_run.failed) if cut_run else []
    if _red(slim_run):
        verdict = "caught"
    elif _red(cut_run):
        verdict = "lost"
    else:
        verdict = "not caught by either" if covering else "no test runs the fixed lines"
    return {"verdict": verdict, "cut_failed": cut_failed, "slim_selected": len(slim_sel)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for arg in ("base", "slim", "python", "map", "plan", "profile_before", "profile_after", "out"):
        p.add_argument(f"--{arg.replace('_', '-')}", required=True)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--budget", type=float, default=900, help="seconds per pytest run")
    a = p.parse_args()
    base, slim = Path(a.base).resolve(), Path(a.slim).resolve()
    for wt in (base, slim):
        runner.require_scratch_worktree(wt)
    changed = runner.git(base, "diff", "--name-only", "HEAD", runner.git(slim, "rev-parse", "HEAD").strip())
    src = [f for f in changed.splitlines() if f.endswith(".py") and not runner.is_test_file(f)]
    if src:
        raise SystemExit(f"base and slim differ in source files {src}; the replay needs identical source.")
    failing = set(runner.read_json(a.profile_before)["failed"])
    cover: dict = {}
    for t, fs in runner.read_json(a.map)["tests"].items():
        if t in failing:
            continue
        for f, ls in fs.items():
            for ln in ls:
                cover.setdefault((f, ln), []).append(t)
    ctx = {"base": base, "slim": slim, "python": a.python, "budget": a.budget, "cover": cover,
           "cut": {r["test"] for r in runner.read_json(a.plan)["cut"]},
           "slim_ids": set(runner.collect_ids(a.python, slim)) - set(runner.read_json(a.profile_after)["failed"])}
    rows = []
    for sha, subject, files in fix_commits(base, a.n):
        row = {"sha": sha, "subject": subject, **replay_one(sha, files, ctx)}
        print(f"{sha[:8]} {row['verdict']:<28} {subject[:60]}")
        rows.append(row)
    runner.write_json(a.out, {"rows": rows})


if __name__ == "__main__":
    main()
