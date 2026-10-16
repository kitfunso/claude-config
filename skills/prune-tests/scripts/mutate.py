"""Kill matrix: plant small bugs on lines the candidate tests cover, record which tests catch each.

  kill    mutants on candidate-covered lines -> kills.json
  verify  re-plant every bug a cut test caught, on the slim branch -> verify.json
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import random
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

import runner

CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq,
       ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}
BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
SYM = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
       ast.Is: "is", ast.IsNot: "is not", ast.In: "in", ast.NotIn: "not in",
       ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


@dataclass(frozen=True)
class Mutant:
    id: str
    file: str
    line: int
    start: int  # UTF-8 byte offsets, the unit ast positions use
    end: int
    new: str
    desc: str


def _stringy(node: ast.BinOp) -> bool:
    return any(isinstance(s, ast.JoinedStr) or (isinstance(s, ast.Constant) and isinstance(s.value, str))
               for s in (node.left, node.right))


def _variants(node: ast.AST):
    """Yield (span node, replacement source, description) for each plausible bug at node."""
    if isinstance(node, ast.Compare):
        for i, op in enumerate(node.ops):
            swap = CMP.get(type(op))
            if swap:
                ops = [*node.ops[:i], swap(), *node.ops[i + 1:]]
                new = ast.Compare(node.left, ops, node.comparators)
                yield node, f"({ast.unparse(new)})", f"{SYM[type(op)]} -> {SYM[swap]}"
    elif isinstance(node, ast.BinOp) and type(node.op) in BIN and not _stringy(node):
        swap = BIN[type(node.op)]
        new = ast.BinOp(node.left, swap(), node.right)
        yield node, f"({ast.unparse(new)})", f"{SYM[type(node.op)]} -> {SYM[swap]}"
    elif isinstance(node, ast.BoolOp):
        swap = ast.Or if isinstance(node.op, ast.And) else ast.And
        yield node, f"({ast.unparse(ast.BoolOp(swap(), node.values))})", "and <-> or"
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub)):
        yield node, f"({ast.unparse(node.operand)})", "drop not" if isinstance(node.op, ast.Not) else "drop -"
    elif isinstance(node, ast.Constant) and type(node.value) is bool:
        yield node, str(not node.value), f"{node.value} -> {not node.value}"
    elif isinstance(node, ast.Constant) and type(node.value) in (int, float):
        yield node, repr(node.value + 1), f"{node.value!r} -> {node.value + 1!r}"
    elif isinstance(node, ast.Return) and node.value is not None and not (
            isinstance(node.value, ast.Constant) and node.value.value is None):
        yield node, "return None", "return -> return None"
    elif isinstance(node, (ast.If, ast.While, ast.IfExp)) and not isinstance(
            node.test, (ast.Compare, ast.BoolOp, ast.UnaryOp)):
        yield node.test, f"(not ({ast.unparse(node.test)}))", "cond -> not cond"


def mutants_for(repo: Path, rel: str, lines: set[int]) -> list[Mutant]:
    src = (repo / rel).read_bytes()
    starts = [0]
    for chunk in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(chunk))
    out: list[Mutant] = []
    for node in ast.walk(ast.parse(src)):
        for span, new, desc in _variants(node):
            if span.lineno not in lines:
                continue
            a = starts[span.lineno - 1] + span.col_offset
            b = starts[span.end_lineno - 1] + span.end_col_offset
            try:
                compile(src[:a] + new.encode() + src[b:], rel, "exec")
            except (SyntaxError, ValueError):
                continue
            out.append(Mutant(f"{rel}:{span.lineno}:{len(out)}", rel, span.lineno, a, b, new, desc))
    return out


def _drop_pyc(path: Path) -> None:
    for pyc in path.parent.glob(f"__pycache__/{path.stem}.*.pyc"):
        pyc.unlink(missing_ok=True)


class Planted:
    """Context manager: the mutant is on disk inside the block, the original after it."""

    def __init__(self, root: Path, m: Mutant):
        self.path, self.m = root / m.file, m

    def __enter__(self):
        self.original = self.path.read_bytes()
        _drop_pyc(self.path)
        self.path.write_bytes(self.original[:self.m.start] + self.m.new.encode() + self.original[self.m.end:])

    def __exit__(self, *exc):
        self.path.write_bytes(self.original)
        _drop_pyc(self.path)


def _batch_killers(run: runner.Run, tests: list[str], root: Path, ctx: dict) -> set[str]:
    # kill checks every node id collects first, so rc 4 here is a bug that broke conftest loading
    if run.rc == 4 or run.collect_errors or (run.rc in (2, 3) and not run.failed):
        return set(tests)  # the bug broke import or collection: the whole batch goes red
    return set(runner.red_tests(ctx["python"], root, run, tests, lambda t: _timeout([t], ctx["dur"])))


def _timeout(tests: list[str], durations: dict) -> float:
    return 3 * sum(durations.get(t, 1.0) for t in tests) + 60


def run_mutant(m: Mutant, root: Path, ctx: dict) -> dict:
    tests = ctx["cover"].get((m.file, m.line), [])
    cands = [t for t in tests if t in ctx["cands"]]
    keepers = sorted((t for t in tests if t not in ctx["cands"]), key=lambda t: ctx["dur"].get(t, 0))
    keeper, keeper_status = None, "not-run"
    with Planted(root, m):
        run = runner.run_pytest(ctx["python"], root, cands, timeout=_timeout(cands, ctx["dur"]))
        killers = _batch_killers(run, cands, root, ctx)
        if killers and keepers:
            k = runner.run_pytest(ctx["python"], root, keepers, stop_first=True, timeout=ctx["budget"])
            caught = k.failed if k.timed_out else _batch_killers(k, keepers, root, ctx)
            keeper = min(caught) if caught else None
            keeper_status = "budget" if k.timed_out and not caught else "ran"
    status = "no-candidate-catch" if not killers else ("shared" if keeper else "candidate-only")
    return {**asdict(m), "cand_killers": sorted(killers), "keeper_killer": keeper,
            "keeper_status": keeper_status, "status": status}


def _sanity(root: Path, rel: str, tests: list[str], python: str) -> None:
    """Break the target file outright; its covering tests must go red or the run is blind."""
    path = root / rel
    original = path.read_bytes()
    try:
        _drop_pyc(path)
        path.write_bytes(b'raise RuntimeError("prune-tests sanity")\n' + original)
        run = runner.run_pytest(python, root, tests[:3], timeout=600)
    finally:
        path.write_bytes(original)
        _drop_pyc(path)
    if not (run.failed or run.collect_errors or run.rc in (2, 3, 4)):
        raise SystemExit(f"Sanity failed: breaking {rel} left {tests[:3]} green. "
                         "The tests are not running this worktree's code.")


def _workers(base: Path, out: Path, n: int, prefix: str = "wt") -> list[Path]:
    roots = [base]
    extra = [p for p in runner.git(base, "ls-files", "--others").splitlines() if "__pycache__" not in p]
    for k in range(1, n):
        wt = out / f"{prefix}-{k}" / base.name  # same folder name: a root __init__.py imports through it
        if wt.exists():
            runner.git(wt, "checkout", "--", ".")  # a crashed run can leave a mutant planted
        else:
            runner.git(base, "worktree", "add", "--detach", str(wt), "HEAD")
        for rel in extra:
            (wt / rel).parent.mkdir(parents=True, exist_ok=True)
            (wt / rel).unlink(missing_ok=True)
            # a hardlinked secret stays one file on disk; anything the code may write stays a copy
            (os.link if (base / rel).stat().st_nlink > 1 else shutil.copy2)(base / rel, wt / rel)
        roots.append(wt)
    return roots


def kill(a: argparse.Namespace) -> None:
    base = Path(a.repo).resolve()
    runner.require_scratch_worktree(base)
    tests_map = runner.read_json(a.map)["tests"]
    cdoc = runner.read_json(a.candidates)
    cands = set(cdoc["candidates"])
    dur = runner.read_json(a.profile)["tests"]
    skip = set(cdoc["failing_at_baseline"])  # a test red before any bug would "catch" every bug
    for path in a.skip or ():  # a plan.json skips its cut tests; a text file lists node ids
        skip |= ({r["test"] for r in runner.read_json(path)["cut"]} if path.endswith(".json")
                 else set(filter(None, Path(path).read_text(encoding="utf-8").splitlines())))
    stale = sorted(set(tests_map) - skip - set(runner.collect_ids(a.python, base)))
    if stale:
        raise SystemExit(f"{len(stale)} map node ids do not collect in {base}, e.g. {stale[:3]}; remap.")
    cover: dict = {}
    targets: dict = {}
    for t, files in tests_map.items():
        if t in skip:
            continue
        for f, lines in files.items():
            for ln in lines:
                cover.setdefault((f, ln), []).append(t)
            if t in cands:
                targets.setdefault(f, set()).update(lines)
    files = sorted(f for f in targets if not a.files or any(fnmatch.fnmatch(f, g) for g in a.files))
    mutants = [m for f in files for m in mutants_for(base, f, targets[f])]
    total = len(mutants)
    if a.max_mutants and total > a.max_mutants:
        # SHORTCUT: uniform sample caps run time; a cut decided on a sample is weaker evidence
        mutants = random.Random(0).sample(mutants, a.max_mutants)
    print(f"{len(mutants)} of {total} mutants on {len(files)} files, {len(cands)} candidate tests")
    if not mutants:
        raise SystemExit("No mutants: the candidates cover no mutable lines.")
    busiest = max(files, key=lambda f: sum(m.file == f for m in mutants))
    _sanity(base, busiest, sorted({t for (f, _), ts in cover.items() if f == busiest for t in ts if t in cands}),
            a.python)
    out = Path(a.out).resolve()
    # results land in a JSON-lines file as they finish, so a crashed run resumes where it stopped
    partial = out.with_suffix(".partial.jsonl")
    done = {}
    if partial.exists():
        done = {r["id"]: r for r in map(json.loads, partial.read_text(encoding="utf-8").splitlines())}
    todo = [m for m in mutants if m.id not in done]
    roots = _workers(base, out.parent, a.workers)
    ctx = {"cover": cover, "cands": cands, "dur": dur, "python": a.python, "budget": a.budget}
    lock = threading.Lock()

    def work(chunk: list[Mutant], root: Path) -> None:
        for m in chunk:
            row = run_mutant(m, root, ctx)
            with lock:
                with partial.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
                done[m.id] = row
                if len(done) % 25 == 0:
                    print(f"{len(done)}/{len(mutants)} mutants done", flush=True)

    with ThreadPoolExecutor(len(roots)) as pool:
        list(pool.map(work, [todo[k::len(roots)] for k in range(len(roots))], roots))
    for wt in roots[1:]:
        runner.git(base, "worktree", "remove", "--force", str(wt))
        wt.parent.rmdir()
    rows = [done[m.id] for m in mutants]
    shas = {f: hashlib.sha256((base / f).read_bytes()).hexdigest() for f in files}
    runner.write_json(out, {"mutants": rows, "total_mutants": total, "sampled": len(mutants) < total,
                            "file_sha256": shas})
    by = {s: sum(r["status"] == s for r in rows) for s in ("candidate-only", "shared", "no-candidate-catch")}
    print(f"wrote {out}: {by}")


def verify(a: argparse.Namespace) -> None:
    slim = Path(a.repo).resolve()
    runner.require_scratch_worktree(slim)
    ids = set(runner.collect_ids(a.python, slim))
    jobs = []
    for kpath, ppath in zip(a.kills, a.plan, strict=True):
        jobs += _verify_jobs(slim, runner.read_json(kpath), runner.read_json(ppath), ids)
    roots = _workers(slim, Path(a.out).resolve().parent, a.workers, prefix="vw")
    rows, lock = [], threading.Lock()

    def work(chunk: list[tuple[Mutant, list[str]]], root: Path) -> None:
        for mut, sel in chunk:
            caught = False  # no test left to run: pytest with no ids would run the whole suite
            if sel:
                with Planted(root, mut):
                    run = runner.run_pytest(a.python, root, sel, stop_first=True, timeout=a.budget)
                    caught = runner.is_red(run) or any(runner.red_tests(a.python, root, run, sel, lambda t: a.budget))
            with lock:
                rows.append({"id": mut.id, "desc": mut.desc, "selected": sel, "caught": caught})
                if len(rows) % 25 == 0:
                    print(f"{len(rows)}/{len(jobs)} re-planted", flush=True)

    with ThreadPoolExecutor(len(roots)) as pool:
        list(pool.map(work, [jobs[k::len(roots)] for k in range(len(roots))], roots))
    for wt in roots[1:]:
        runner.git(slim, "worktree", "remove", "--force", str(wt))
        wt.parent.rmdir()
    rows.sort(key=lambda r: r["id"])
    lost = [r for r in rows if not r["caught"]]
    runner.write_json(a.out, {"checked": len(rows), "lost": lost, "rows": rows})
    print(f"verify: {len(rows)} re-planted bugs, {len(lost)} lost")


def _verify_jobs(slim: Path, kdoc: dict, plan: dict, ids: set) -> list[tuple[Mutant, list[str]]]:
    jobs = []
    for m in kdoc["mutants"]:
        claimed = plan["catchers"].get(m["id"])
        if claimed is None:
            continue  # no cut test caught it: the slim suite is unchanged for this bug
        if hashlib.sha256((slim / m["file"]).read_bytes()).hexdigest() != kdoc["file_sha256"][m["file"]]:
            raise SystemExit(f"{m['file']} differs from the analysed source; a cut must only touch tests.")
        sel = [t for t in claimed if t in ids] or sorted(
            t for t in ids if t.split("::")[0] in {c.split("::")[0] for c in claimed})
        jobs.append((Mutant(**{k: m[k] for k in Mutant.__dataclass_fields__}), sel))
    return jobs


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kill")
    k.add_argument("--repo", required=True, help="scratch worktree of the pre-cut commit")
    k.add_argument("--python", required=True)
    k.add_argument("--map", required=True)
    k.add_argument("--candidates", required=True)
    k.add_argument("--profile", required=True)
    k.add_argument("--out", required=True)
    k.add_argument("--files", nargs="*", help="glob filter on source files to mutate")
    k.add_argument("--max-mutants", type=int, default=0)
    k.add_argument("--workers", type=int, default=1)
    k.add_argument("--budget", type=float, default=120, help="seconds for the keeper run per mutant")
    k.add_argument("--skip", nargs="*", help="tests left out of this pass: a node-id list file or a plan.json")
    v = sub.add_parser("verify")
    v.add_argument("--repo", required=True, help="scratch worktree of the slim branch")
    v.add_argument("--python", required=True)
    v.add_argument("--kills", nargs="+", required=True, help="one per pass, in the order of --plan")
    v.add_argument("--plan", nargs="+", required=True)
    v.add_argument("--out", required=True)
    v.add_argument("--budget", type=float, default=600)
    v.add_argument("--workers", type=int, default=1)
    a = p.parse_args()
    kill(a) if a.cmd == "kill" else verify(a)


if __name__ == "__main__":
    main()
