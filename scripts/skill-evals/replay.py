"""Replay a past campaign: headless Claude Code runs on frozen data, scored on truth the run never sees.

Usage: python replay.py CASE_DIR [--arms with without] [--runs 1] [--budget-min N] [--parallel 4]
The score is the gain over the case's naive baseline, in the metric's units, per wall-clock hour.
A run whose transcript touches a forbidden path is void.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

# Outside the home folder, so no parent CLAUDE.md loads and no hippo store is found by walking up.
OUT = Path("C:/qmp-replays")
CACHE = Path.home() / "skill-eval-runs" / "replay-cache"
GRACE_S = 300
MIN_LEG_S = 180
MAX_LEGS = 12
FORBID_ALWAYS = (".hippo", ".claude/projects", "quant-ml-protocol/evals", "quant-ml-protocol/replays",
                 "replay-cache", "skill-eval-runs", "hippo recall", "hippo context", "qmp-replays/runs/")
FORBID_WITHOUT = ("skills/quant-ml-protocol",)
TSV_COLS = ("run_id", "case", "arm", "budget", "minutes", "timed_out", "value", "naive", "gain", "gain_per_hour",
            "void", "skill_used", "turns", "output_tokens")


@dataclass(frozen=True)
class Audit:
    void: str
    skill_used: bool
    turns: int
    output_tokens: int


def tool_uses(lines: list[str]) -> list[dict]:
    """Every tool_use block in a stream-json transcript, sub-agents' included."""
    uses = []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        content = (event.get("message") or {}).get("content")
        if isinstance(content, list):
            uses += [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    return uses


def audit(lines: list[str], arm: str, forbid: tuple[str, ...], work: str) -> Audit:
    uses = tool_uses(lines)
    banned = FORBID_ALWAYS + forbid + (FORBID_WITHOUT if arm == "without" else ())
    own = work.replace("\\", "/").lower()
    void = ""
    for use in uses:
        # A run's own folder sits under qmp-replays/runs/; only its siblings are banned.
        text = json.dumps(use.get("input", {})).replace("\\\\", "/").lower().replace(own, "<work>")
        hit = next((f for f in banned if f.lower() in text), None)
        if hit:
            void = f"{use.get('name')} touched '{hit}'"
            break
    skill_used = any(u.get("name") == "Skill" and "quant-ml-protocol" in json.dumps(u.get("input", {}))
                     for u in uses)
    if arm == "without" and skill_used and not void:
        void = "used the skill in the without arm"
    # A resumed run writes one result event per session leg; the run's cost is their sum.
    results = [json.loads(l) for l in lines if '"type":"result"' in l.replace(" ", "")]
    turns = sum(int(r.get("num_turns") or 0) for r in results)
    out = sum(int((r.get("usage") or {}).get("output_tokens") or 0) for r in results)
    return Audit(void, skill_used, turns, out)


def gain(value: float | None, naive: float, lower_is_better: bool) -> float | None:
    if value is None:
        return None
    return naive - value if lower_is_better else value - naive


def prompt(case: dict, arm: str, budget_min: int, deadline: str) -> str:
    skill =("Run the campaign with the quant-ml-protocol skill: load it with the Skill tool first."
             if arm == "with" else
             "Work from your own knowledge: use no skill and read nothing under ~/.claude/skills.")
    return "\n".join([
        "Read BRIEF.md in this folder and do the task it sets.", skill, "",
        f"You have {budget_min} minutes of wall-clock time from now; the run is stopped at {deadline} local time.",
        f"Keep {case['submission']} in this folder updated with your best predictions as you go. When time runs out,",
        "the file on disk is what gets scored, and a missing file scores nothing.",
        "Work only inside this folder and its data. Reading, listing or searching anywhere else voids the run.",
        "Nobody will answer questions: decide, keep improving, and stop only when the time is up.",
    ])


def nudge(case: dict, minutes_left: float, deadline: str) -> str:
    return (f"The run is not over: about {int(minutes_left)} minutes remain before it is stopped at {deadline}. "
            f"Keep improving {case['submission']} from where you are, keep the file updated, and keep working "
            "inside this folder until the time is up.")


def drive(base: list[str], first: str, case: dict, work: Path, env: dict, budget_min: int, deadline: str) -> bool:
    """Run one session, resuming it while time remains, so every arm spends the same budget. True if killed."""
    end = time.monotonic() + budget_min * 60
    message, resume = first, []
    with open(work / "transcript.jsonl", "a", encoding="utf-8") as log:
        for _ in range(MAX_LEGS):
            left = end - time.monotonic()
            proc = subprocess.Popen(base + resume + ["-p", message], cwd=work, stdout=log,
                                    stderr=subprocess.STDOUT, env=env)
            try:
                proc.wait(timeout=max(left, 0) + GRACE_S)
            except subprocess.TimeoutExpired:
                kill_tree(proc.pid)
                return True
            left = end - time.monotonic()
            if left < MIN_LEG_S:
                return False
            message, resume = nudge(case, left / 60, deadline), ["--continue"]
    return False


def kill_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        os.killpg(pid, 9)


def prepare(case_dir: Path, case: dict) -> Path:
    cache = CACHE / case["name"]
    if not (cache / "public").is_dir():
        subprocess.run([sys.executable, str(case_dir / "prepare.py"), str(cache)], check=True)
    return cache


def run_one(case_dir: Path, case: dict, cache: Path, arm: str, n: int, budget_min: int) -> dict:
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{case['name']}-{arm}-{n}"
    work = OUT / "runs" / run_id
    (work / "data").mkdir(parents=True)
    for f in (cache / "public").iterdir():
        shutil.copy2(f, work / "data" / f.name)
    (work / "BRIEF.md").write_text(case["brief"], encoding="utf-8")
    base = ["claude", "--model", case.get("model", "opus"), "--permission-mode", "bypassPermissions",
            "--output-format", "stream-json", "--verbose",
            "--disallowedTools", "WebSearch", "WebFetch", *(["Skill"] if arm == "without" else [])]
    env = {**os.environ, "CLAUDE_HIPPO_RECALL": "off", "HIPPO_HOME": str(OUT / "empty-hippo"),
           "HIPPO_SKIP_AUTO_INTEGRATIONS": "1"}
    started = time.monotonic()
    deadline = time.strftime("%H:%M", time.localtime(time.time() + budget_min * 60))
    timed_out = drive(base, prompt(case, arm, budget_min, deadline), case, work, env, budget_min, deadline)
    minutes = (time.monotonic() - started) / 60
    lines = (work / "transcript.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()
    checked = audit(lines, arm, tuple(case.get("forbid", ())), str(work))
    graded = subprocess.run([sys.executable, str(case_dir / "grade.py"), str(work / case["submission"]),
                             str(cache / "private")], capture_output=True, text=True, check=True)
    score = json.loads(graded.stdout)
    g = gain(score.get("value"), score["naive"], score["lower_is_better"])
    row = {"run_id": run_id, "case": case["name"], "arm": arm, "budget": budget_min, "minutes": round(minutes, 1),
           "timed_out": timed_out, "value": score.get("value"), "naive": score["naive"], "gain": g,
           # Per budgeted hour, so a run that stops early gains no rate from it.
           "gain_per_hour": None if g is None else round(g / (budget_min / 60), 3),
           "void": checked.void, "skill_used": checked.skill_used, "turns": checked.turns,
           "output_tokens": checked.output_tokens}
    (work / "result.json").write_text(json.dumps({**row, "grade": score, "audit": asdict(checked)}, indent=1),
                                      encoding="utf-8")
    return row


def append_tsv(rows: list[dict]) -> Path:
    path = OUT / "replays.tsv"
    new = not path.exists()
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write("\t".join(TSV_COLS) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in TSV_COLS) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case_dir", type=Path)
    ap.add_argument("--arms", nargs="+", default=["with", "without"], choices=("with", "without"))
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--budget-min", type=int)
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args(argv)
    case = yaml.safe_load((a.case_dir / "case.yaml").read_text(encoding="utf-8"))
    budget = a.budget_min or int(case["budget_minutes"])
    cache = prepare(a.case_dir, case)
    jobs = [(arm, n) for n in range(1, a.runs + 1) for arm in a.arms]
    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        rows = list(pool.map(lambda j: run_one(a.case_dir, case, cache, j[0], j[1], budget), jobs))
    print(json.dumps(rows, indent=1))
    print(f"ledger: {append_tsv(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
