"""prune-tests analysis: where the minutes go, which tests overlap, what to cut, the report.

  profile  time N full (or selected) runs              -> profile JSON
  map      per-test coverage contexts                  -> map.json
  subsets  tests whose lines sit inside another test's  -> candidates.json
  plan     greedy set cover over the kill matrix        -> plan.json (cut ledger)
  split    light and heavy candidates for a two-pass kill run
  merge    one plan.json from the two passes
  report   everything in the run folder                 -> report.html
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import statistics
import time
from collections import Counter
from pathlib import Path

import runner
from report import write_report

HEAVY_SHARE = 0.5  # heavy = the slowest tests that together take half the test time...
HEAVY_RATIO = 10   # ...and each run at least this many times the median test


def profile(a: argparse.Namespace) -> None:
    repo = Path(a.repo).resolve()
    start = time.monotonic()
    ids = runner.collect_ids(a.python, repo, a.pytest_args)
    collect_s = time.monotonic() - start
    runs = [runner.run_pytest(a.python, repo, a.pytest_args) for _ in range(a.runs)]
    walls = [round(r.seconds, 1) for r in runs]
    first = runs[0]
    runner.write_json(a.out, {"args": a.pytest_args, "collect_s": round(collect_s, 1), "n_collected": len(ids),
                  "walls": walls, "median_wall": statistics.median(walls), "tests": first.durations,
                  "outcomes": first.outcomes, "failed": sorted(set().union(*(r.failed for r in runs)))})
    print(f"{len(ids)} tests, collect {collect_s:.0f}s, walls {walls}, failed {len(first.failed)}")


def map_(a: argparse.Namespace) -> None:
    import coverage

    repo = os.path.realpath(a.repo)
    data_file = Path(a.out).resolve().with_suffix(".coverage")
    data_file.unlink(missing_ok=True)
    run = runner.run_pytest(a.python, Path(repo), a.pytest_args, coverage_file=data_file)
    data = coverage.CoverageData(basename=str(data_file))
    data.read()
    tests: dict = {t: {} for t in run.outcomes}
    for f in data.measured_files():
        rel = Path(os.path.relpath(os.path.realpath(f), repo)).as_posix()
        if rel.startswith("..") or runner.is_test_file(rel):
            continue
        for line, ctxs in (data.contexts_by_lineno(f) or {}).items():
            for c in ctxs:
                if c:
                    tests.setdefault(c, {}).setdefault(rel, set()).add(line)
    tests = {t: {f: sorted(ls) for f, ls in fs.items()} for t, fs in tests.items()}
    runner.write_json(a.out, {"tests": tests, "failed": sorted(run.failed), "seconds": round(run.seconds, 1)})
    print(f"mapped {len(tests)} tests in {run.seconds:.0f}s, {len(run.failed)} failed")


def subsets(a: argparse.Namespace) -> None:
    m, prof = runner.read_json(a.map), runner.read_json(a.profile)
    failing = set(m["failed"]) | set(prof["failed"])
    exempt = sorted(t for t in m["tests"] if any(fnmatch.fnmatch(t, g) for g in a.exempt))
    sets = {t: frozenset((f, ln) for f, ls in fs.items() for ln in ls)
            for t, fs in m["tests"].items() if t not in failing}
    index: dict = {}
    for t, s in sets.items():
        for e in s:
            index.setdefault(e, set()).add(t)
    cands = {}
    for t, s in sets.items():
        if not s or t in exempt:
            continue
        rare = min(s, key=lambda e: len(index[e]))
        sups = [u for u in index[rare] if u != t and len(sets[u]) >= len(s) and s <= sets[u]]
        if sups:
            cands[t] = min(sups, key=lambda u: (len(sets[u]), u))
    no_cov = sorted(t for t, s in sets.items() if not s and t not in exempt)
    runner.write_json(a.out, {"candidates": cands, "no_coverage": no_cov, "exempt": exempt,
                  "failing_at_baseline": sorted(failing)})
    print(f"{len(cands)} candidates, {len(no_cov)} with no coverage, {len(exempt)} exempt, "
          f"{len(failing)} failing at baseline")


def _heavy(dur: dict) -> list[str]:
    if not dur:
        return []
    total, med = sum(dur.values()), statistics.median(dur.values())
    out, acc = [], 0.0
    for t, s in sorted(dur.items(), key=lambda kv: -kv[1]):
        if acc >= HEAVY_SHARE * total or s < HEAVY_RATIO * med:
            break
        out.append(t)
        acc += s
    return out


def _set_cover(universe: dict, dur: dict) -> list[str]:
    kept, left = [], dict(universe)
    while left:
        counts = Counter(t for ks in left.values() for t in ks)
        # most bugs, then fastest in whole seconds, then first name: the first test's import time
        # must not flip the pick between two equal sub-second tests
        best = max(sorted(counts), key=lambda t: (counts[t], -round(dur.get(t, 0.0))))
        kept.append(best)
        left = {mid: ks for mid, ks in left.items() if best not in ks}
    return kept


def plan(a: argparse.Namespace) -> None:
    kd, cd, prof, m = (runner.read_json(p) for p in (a.kills, a.candidates, a.profile, a.map))
    dur, rows = prof["tests"], kd["mutants"]
    universe = {r["id"]: set(r["cand_killers"]) for r in rows if r["status"] == "candidate-only"}
    kept = _set_cover(universe, dur)
    cut = sorted(set(cd["candidates"]) - set(kept))
    catchers = {}
    for r in rows:
        ks = set(r["cand_killers"])
        if ks & set(cut):
            catchers[r["id"]] = [r["keeper_killer"]] if r["keeper_killer"] else sorted(ks & set(kept))
    planted = Counter()
    for r in rows:
        for t, fs in ((t, m["tests"].get(t, {})) for t in cd["candidates"]):
            if r["line"] in fs.get(r["file"], ()):
                planted[t] += 1
    ledger = []
    for t in cut:
        mine = [r for r in rows if t in r["cand_killers"]]
        if mine:
            reason = f"each of the {len(mine)} planted bugs it catches is also caught by the tests listed"
        elif planted[t]:
            reason = f"catches none of the {planted[t]} planted bugs on its lines"
        else:
            reason = "no mutable line it runs; read it before cutting"
        ledger.append({"test": t, "reason": reason, "caught_by": sorted({c for r in mine for c in catchers[r["id"]]}),
                       "lines_inside": cd["candidates"][t], "seconds": round(dur.get(t, 0.0), 2)})
    only = Counter(t for ks in universe.values() for t in ks if t in kept)
    runner.write_json(a.out, {"cut": ledger, "kept": [{"test": t, "bugs_only_candidates_catch": only[t]} for t in kept],
                  "catchers": catchers, "heavy": _heavy(dur), "sampled": kd["sampled"],
                  "survivors": sum(r["status"] == "no-candidate-catch" for r in rows),
                  "unsure_keeper_runs": sum(r["keeper_status"] not in ("ran", "not-run") for r in rows)})
    print(f"cut {len(cut)}, keep {len(kept)} candidates for unique catches, heavy {len(_heavy(dur))}")


def split(a: argparse.Namespace) -> None:
    """Heavy candidates dominate a kill run; score light ones first, heavy ones second."""
    cd, dur = runner.read_json(a.candidates), runner.read_json(a.profile)["tests"]
    heavy = {t: s for t, s in cd["candidates"].items() if dur.get(t, 0.0) > a.seconds}
    light = {t: s for t, s in cd["candidates"].items() if t not in heavy}
    out = Path(a.out_dir)
    runner.write_json(out / "candidates-light.json", {**cd, "candidates": light})
    runner.write_json(out / "candidates-heavy.json", {**cd, "candidates": heavy})
    (out / "skip-heavy.txt").write_text("\n".join(sorted(heavy)), encoding="utf-8")
    (out / "skip-light.txt").write_text("\n".join(sorted(light)), encoding="utf-8")
    print(f"{len(light)} light, {len(heavy)} heavy candidates (over {a.seconds}s)")


def merge_plans(a: argparse.Namespace) -> None:
    plans = [runner.read_json(p) for p in a.plans]
    # a test one pass names as a catcher stays, even when the other pass would cut it
    relied = {t for p in plans for ts in p["catchers"].values() for t in ts}
    cut = {r["test"]: r for p in plans for r in p["cut"] if r["test"] not in relied}
    runner.write_json(a.out, {
        "cut": list(cut.values()), "kept": [r for p in plans for r in p["kept"]],
        "catchers": {k: v for p in plans for k, v in p["catchers"].items()}, "heavy": plans[0]["heavy"],
        "sampled": any(p["sampled"] for p in plans), "survivors": sum(p["survivors"] for p in plans),
        "unsure_keeper_runs": sum(p["unsure_keeper_runs"] for p in plans)})


def grade(a: argparse.Namespace) -> None:
    """Grade a cut that already landed: what it removed, and the lines no remaining test runs."""
    m, prof = runner.read_json(a.map)["tests"], runner.read_json(a.profile)
    failing = set(prof["failed"])
    slim_ids = set(runner.collect_ids(a.python, Path(a.slim).resolve()))
    removed = sorted(t for t in set(prof["outcomes"]) - slim_ids if t not in failing)
    ran: dict = {}
    for t in slim_ids - failing:
        for f, ls in m.get(t, {}).items():
            ran.setdefault(f, set()).update(ls)
    orphan: dict = {}
    for t in removed:
        lines = {f: sorted(set(ls) - ran.get(f, set())) for f, ls in m.get(t, {}).items()}
        if any(lines.values()):
            orphan[t] = {f: ls for f, ls in lines.items() if ls}
    out = Path(a.out_dir)
    runner.write_json(out / "removed.json", {"cut": [{"test": t} for t in removed]})
    runner.write_json(out / "map-orphan.json", {"tests": orphan, "failed": []})
    runner.write_json(out / "candidates-removed.json", {"candidates": {t: "removed" for t in orphan},
                                                         "no_coverage": [], "exempt": [],
                                                         "failing_at_baseline": sorted(failing)})
    lines = {(f, ln) for fs in orphan.values() for f, ls in fs.items() for ln in ls}
    print(f"{len(removed)} tests removed; {len(lines)} lines no remaining test runs, "
          f"{len(orphan)} removed tests ran them")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("profile", "map"):
        s = sub.add_parser(name, help="extra pytest args go after --")
        s.add_argument("--repo", required=True)
        s.add_argument("--python", required=True)
        s.add_argument("--out", required=True)
        s.add_argument("pytest_args", nargs="*")
        if name == "profile":
            s.add_argument("--runs", type=int, default=3)
    s = sub.add_parser("subsets")
    s.add_argument("--map", required=True)
    s.add_argument("--profile", required=True)
    s.add_argument("--exempt", nargs="*", default=[], help="node id globs that are never candidates")
    s.add_argument("--out", required=True)
    s = sub.add_parser("plan")
    for arg in ("kills", "candidates", "profile", "map", "out"):
        s.add_argument(f"--{arg}", required=True)
    s = sub.add_parser("split")
    s.add_argument("--candidates", required=True)
    s.add_argument("--profile", required=True)
    s.add_argument("--seconds", type=float, default=2.0)
    s.add_argument("--out-dir", required=True)
    s = sub.add_parser("merge", help="one plan.json from the light and heavy passes")
    s.add_argument("--plans", nargs="+", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("grade", help="grade a cut that already landed")
    s.add_argument("--map", required=True, help="map.json of the commit before the cut")
    s.add_argument("--profile", required=True)
    s.add_argument("--slim", required=True, help="scratch worktree of the cut commit")
    s.add_argument("--python", required=True)
    s.add_argument("--out-dir", required=True)
    s = sub.add_parser("report")
    s.add_argument("--dir", required=True, help="run folder holding the JSON files")
    s.add_argument("--out", required=True)
    a = p.parse_args()
    {"profile": profile, "map": map_, "subsets": subsets, "plan": plan, "split": split, "merge": merge_plans,
     "grade": grade, "report": lambda a: write_report(Path(a.dir), Path(a.out))}[a.cmd](a)


if __name__ == "__main__":
    main()
