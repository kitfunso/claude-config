#!/usr/bin/env python3
"""Weekly scorecard for the Claude Code config in ~/.claude: seven metrics, each scored 0..1, averaged into a score out of 100.

Usage: python scorecard.py [--days 7] [--no-fetch]
Appends one JSON line to ~/.claude/scorecard/history.jsonl, writes scorecard-YYYY-MM-DD.html beside it, prints a summary.
The scorecard folder stays outside the git allowlist: the repo is public and the page shows local data.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import statistics
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from string import Template

import time_ledger
import token_ledger

CLAUDE = Path.home() / ".claude"
HOOKS = CLAUDE / "scripts" / "hooks"
OUT = CLAUDE / "scorecard"
REPLY_LOG = CLAUDE / "state" / "reply_check.jsonl"
BASELINE_DAYS = 28
PROBATION_DAYS = 30


@dataclass(frozen=True)
class Goal:
    key: str
    name: str
    floor: float
    target: float
    fmt: str
    why: str


GOALS = (
    Goal("approvals", "Approval-only replies a week", 77, 10, "{:.0f}",
         "77 was the week of 17 to 24 Sep; ten a week leaves room for the genuine ASK-FIRST stops."),
    Goal("reply_check", "Reply-check pass rate", 0.5, 0.95, "{:.0%}",
         "Nearly every reply should pass the shape check; the 5% slack covers long answers that were asked for."),
    Goal("critical", "CRITICAL rules with a bound check", 0.0, 1.0, "{:.0%}",
         "A rule without a verifier is a claim: each CRITICAL rule needs a hook or deny that exists and is wired."),
    Goal("sync", "Config in sync", 0.0, 1.0, "{:.1f}",
         "The config is only shared when ~/.claude is a clean checkout, level with origin/main."),
    Goal("evals", "Skill eval pass rate", 0.5, 0.9, "{:.0%}",
         "A skill earns its place in the listing by passing its own evals; 90% allows one miss in ten."),
    Goal("spend", "Spend per task vs the prior 28 days", 1.5, 1.0, "{:.2f}x",
         "Cost per task should not creep; 1.5 times the prior four weeks is a regression to chase."),
    Goal("probation", "Probation rules past 30 days", 1.0, 0.0, "{:.0%}",
         "A probation rule gets 30 days, then the monthly audit drops it or makes it permanent."),
)
RULE_CHECKS = {
    "Capability Existence": ("check_skill_references.py",),
    "Sourcing": ("reply_check.py",),
    "Git Operations": ("git_guard.py",),
    "Hand-Maintained": ("claude_backup.py", "rewrite_gate.py"),
    "Root Cause": ("reply_check.py",),
    "Human Voice": ("human_voice.py", "reply_check.py"),
    "Do It Properly": ("do_it_properly.py", "reply_check.py"),
    "Comments": ("comment_budget_guard.py",),
    "Reports are local HTML": ("deny:Artifact",),
}
PROBATION_FEEDS = {"Human Voice": r"long|table|bullets|banned:.+", "Do It Properly": r"sweeping"}
RULE_LINE = re.compile(r"^(#+ |- \*\*)")
PROBATION = re.compile(r"Set (\d{4}-\d{2}-\d{2}) \(probation\)")
MANUAL_ONLY = re.compile(r"^disable-model-invocation:\s*true\b", re.M)


@dataclass(frozen=True)
class Result:
    value: float | None
    shown: str
    note: str = ""
    details: tuple[str, ...] = ()


def score(value: float | None, floor: float, target: float) -> float:
    """Linear from the floor (0) to the target (1), clipped; a metric with no data scores 0."""
    if value is None:
        return 0.0
    return min(max((value - floor) / (target - floor), 0.0), 1.0)


def overall(scores: list[float]) -> float:
    """Equal-weight mean of the metric scores, out of 100."""
    return 100 * sum(scores) / len(scores) if scores else 0.0


def goal_text(goal: Goal) -> str:
    return f"{'at most' if goal.target < goal.floor else 'at least'} {goal.fmt.format(goal.target)}"


def stamp(when: datetime) -> str:
    """UTC with no zone suffix, so it string-compares correctly with transcript timestamps."""
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def parse_ts(text: object) -> datetime:
    when = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def approvals_metric(rows: list[dict], start: datetime, days: int) -> Result:
    """Approval-only prompts in the window, scaled to a week so the weekly floor and target hold for any --days."""
    if not rows:
        return Result(None, "no data yet", details=("no human prompts in the window",))
    gaps = [gap for gap, _, _ in time_ledger.approval_gaps(rows)]
    weekly = len(gaps) * 7 / days
    shown = f"{len(gaps)} of {len(rows)} prompts" + ("" if days == 7 else f", {weekly:.0f} a week")
    idle = (f"idle median {statistics.median(gaps):.1f} min before each, {sum(min(g, 60) for g in gaps) / 60:.1f} h "
            "with each stop capped at 60 min") if gaps else "no approval-only replies"
    listing = f"each one beside the reply it answered: python ~/.claude/scripts/time_ledger.py --since {stamp(start)} --stops"
    return Result(weekly, shown, details=(idle, listing))


def reply_record(line: str) -> dict | None:
    """One reply-check record with its parsed time under "_ts"; None when the line does not fit the schema."""
    try:
        rec = json.loads(line)
        rec["_ts"] = parse_ts(rec["ts"])
    except (ValueError, KeyError, TypeError):
        return None
    return rec if isinstance(rec.get("flags"), list) else None


def read_reply_log(path: Path, since: datetime) -> tuple[list[dict], int] | None:
    """(records stamped at or after since, unreadable line count); None until the Stop hook has written the log."""
    if not path.exists():
        return None
    parsed = [reply_record(line) for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    return [rec for rec in parsed if rec and rec["_ts"] >= since], sum(rec is None for rec in parsed)


def reply_metric(log: tuple[list[dict], int] | None) -> Result:
    if log is None:
        return Result(None, "no data yet", details=(f"{REPLY_LOG} does not exist yet",))
    records, unreadable = log
    skipped = (f"{unreadable} unreadable lines skipped",) if unreadable else ()
    if not records:
        return Result(None, "no data yet", details=("no replies logged in the window", *skipped))
    passed = sum(not rec["flags"] for rec in records)
    flags = Counter(str(flag) for rec in records for flag in rec["flags"])
    top = ", ".join(f"{flag} {n}" for flag, n in flags.most_common(8)) or "none"
    return Result(passed / len(records), f"{passed / len(records):.0%} of {len(records)} replies",
                  details=(f"{passed} passed with no flags; top flags: {top}", *skipped))


def critical_rules(text: str) -> list[str]:
    """Heading and bold-lead bullet lines tagged (CRITICAL; prose that only mentions CRITICAL is not a rule."""
    return [line for line in text.splitlines() if RULE_LINE.match(line) and "(CRITICAL" in line]


def rule_name(line: str) -> str:
    """Heading text or bold lead, without its (CRITICAL) style tag."""
    head = RULE_LINE.sub("", line.strip()).lstrip("*")
    return re.split(r"\(|\*\*", head)[0].strip(" .:")


def hook_scripts(settings: dict) -> set[str]:
    """File names that settings.json hooks run, read from each hook's command and args."""
    parts = [str(part) for groups in (settings.get("hooks") or {}).values() for group in groups
             for hook in group.get("hooks") or [] for part in [hook.get("command", ""), *(hook.get("args") or [])]]
    return {re.split(r"[\\/]", token)[-1] for part in parts for token in re.split(r"[\s\"']+", part) if token}


def check_gaps(checks: tuple[str, ...], wired: set[str], deny: list[str], hooks_dir: Path) -> list[str]:
    """Why a rule's checks are not bound; empty when every script exists and is wired, and every deny is listed."""
    gaps = []
    for check in checks:
        if check.startswith("deny:"):
            if check[5:] not in deny:
                gaps.append(f"{check[5:]} not in permissions.deny")
        elif not (hooks_dir / check).exists():
            gaps.append(f"{check} missing from scripts/hooks")
        elif check not in wired:
            gaps.append(f"{check} not wired in settings.json")
    return gaps


def critical_metric(files: list[Path], settings: dict, hooks_dir: Path) -> Result:
    rules = [(rule_name(line), path.name) for path in files for line in critical_rules(path.read_text(encoding="utf-8"))]
    if not rules:
        return Result(None, "no data yet", details=("no (CRITICAL) headings or bold-lead bullets found",))
    wired, deny = hook_scripts(settings), (settings.get("permissions") or {}).get("deny") or []
    lines, unchecked = [], []
    for name, source in rules:
        checks = next((c for key, c in RULE_CHECKS.items() if key in name), None)
        gaps = ["no mapping in RULE_CHECKS"] if checks is None else check_gaps(checks, wired, deny, hooks_dir)
        via = ", ".join(c.replace("deny:", "permissions.deny ") for c in checks or ())
        lines.append(f"unchecked: {name} ({source}): {'; '.join(gaps)}" if gaps else f"checked: {name} ({source}) via {via}")
        if gaps:
            unchecked.append(f"{name} (no mapping)" if checks is None else name)
    done = len(rules) - len(unchecked)
    note = "unchecked: " + ", ".join(unchecked) if unchecked else ""
    return Result(done / len(rules), f"{done} of {len(rules)} rules", note=note, details=tuple(lines))


def git(repo: Path, *args: str, timeout: float = 20) -> tuple[bool, str]:
    """(ok, output or error); no optional locks, so a status never rewrites the index of a repo it must not modify."""
    try:
        # The weekly task runs under pythonw, where each console child would flash its own window.
        done = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, text=True,
                              timeout=timeout, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return done.returncode == 0, (done.stdout if done.returncode == 0 else done.stderr).strip()


def sync_metric(repo: Path, fetch: bool) -> Result:
    ok, top = git(repo, "rev-parse", "--show-toplevel")
    if not ok or Path(top).resolve() != repo.resolve():
        return Result(0.0, "not a git checkout", details=(top if not ok else f"{repo} sits inside the checkout at {top}",))
    notes = ["fetch skipped (--no-fetch): compared with the last fetched origin/main"]
    if fetch:
        ok, out = git(repo, "fetch", "--quiet", "origin", timeout=60)
        notes = ["fetched origin" if ok else f"fetch failed, compared with the last fetched origin/main: {out}"]
    ok, status = git(repo, "status", "--porcelain", "--untracked-files=no")
    tree = f"status failed: {status}" if not ok else f"{len(status.splitlines())} tracked files changed" if status else "tracked tree clean"
    clean = ok and not status
    ok, counts = git(repo, "rev-list", "--left-right", "--count", "HEAD...origin/main")
    ahead, behind = (int(n) for n in counts.split()) if ok else (None, None)
    level = ahead == 0 and behind == 0
    where = f"ahead {ahead}, behind {behind} origin/main" if ok else f"no origin/main to compare: {counts}"
    shown = f"{tree}; {'level with origin/main' if level else where}"
    return Result(1.0 if clean and level else 0.5, shown, details=(shown, *notes))


def latest_cases(skills: Path) -> tuple[dict[str, dict[str, tuple[str, list[bool]]]], list[str]]:
    """Per skill, the newest (day, with-skill run passes) of each case still on disk, plus unreadable-file notes.

    A targeted `claude plugin eval --case` rerun replaces only the cases it ran. Result folders are
    named by UTC start time, so sort order is time order."""
    newest: dict[str, dict[str, tuple[str, list[bool]]]] = {}
    bad: list[str] = []
    for path in sorted(skills.glob("*/evals/results/*/aggregate-result.json")):
        skill, day = path.parts[-5], path.parts[-2][:10]
        try:
            runs = {case["name"]: [bool(run["passed"]) for run in case["arms"]["with"]]
                    for case in json.loads(path.read_text(encoding="utf-8"))["cases"]}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            bad.append(f"unreadable: {skill} {path.parts[-2]} ({type(exc).__name__}: {exc})")
            continue
        newest.setdefault(skill, {}).update(
            (name, (day, case_runs)) for name, case_runs in runs.items() if (skills / skill / "evals" / name).is_dir())
    return newest, bad


def manual_only(skill_dir: Path) -> bool:
    """A disable-model-invocation skill never loads in an eval run, so its results measure the runner, not the skill."""
    md = skill_dir / "SKILL.md"
    text = md.read_text(encoding="utf-8", errors="replace") if md.is_file() else ""
    front = text.split("---", 2)[1] if text.startswith("---") else ""
    return bool(MANUAL_ONLY.search(front))


def eval_metric(skills: Path) -> Result:
    newest, bad = latest_cases(skills)
    rates, days, manual = [], [], []
    for skill, cases in newest.items():
        if manual_only(skills / skill):
            manual.append(skill)
            continue
        runs = [passed for _, case_runs in cases.values() for passed in case_runs]
        if runs:
            rates.append((sum(runs) / len(runs), skill, sum(runs), len(runs)))
            days.extend(day for day, _ in cases.values())
        else:
            bad.append(f"no with-skill runs: {skill}")
    if not rates:
        return Result(None, "no data yet", details=tuple(bad) or ("no aggregate-result.json under skills/*/evals/results",))
    rates.sort()
    days.sort()
    mean = statistics.mean(rate for rate, *_ in rates)
    low = ", ".join(f"{skill} {passed}/{total}" for _, skill, passed, total in rates[:3])
    ties = sum(rate == rates[0][0] for rate, *_ in rates)
    skipped = (f"not scored, disable-model-invocation never fires in an eval: {', '.join(manual)}",) if manual else ()
    details = (f"lowest three (with-skill runs passed/total): {low}"
               + (f"; {ties} skills tie at {rates[0][0]:.0%}" if ties > 3 else ""),
               f"newest run per case, dated {days[0]} to {days[-1]}", *skipped, *bad)
    return Result(mean, f"{mean:.0%} mean over {len(rates)} skills", note=f"lowest: {low}", details=details)


def cost_between(since: datetime, until: datetime | None) -> float:
    """Dollars token_ledger prices for requests in [since, until), main threads and subagents."""
    return token_ledger.report(token_ledger.run(stamp(since), stamp(until) if until else "9999"))["total $"]


def spend_metric(window: list[dict], prior: list[dict], cost_now: float, cost_prior: float) -> Result:
    """Dollars per task (a prompt that used a tool) in the window, over the same ratio for the 28 days before it."""
    tasks_now, tasks_prior = sum(r["tools"] > 0 for r in window), sum(r["tools"] > 0 for r in prior)
    first = min((r["t0"] for r in prior), default=None)
    lines = (f"window: ${cost_now:,.0f} over {tasks_now} tasks",
             f"prior {BASELINE_DAYS} days: ${cost_prior:,.0f} over {tasks_prior} tasks"
             + (f", earliest prompt on disk {first:%Y-%m-%d}" if first else ""))
    if not (tasks_now and tasks_prior and cost_prior > 0):
        return Result(None, "no data yet", details=lines)
    now_each, prior_each = cost_now / tasks_now, cost_prior / tasks_prior
    return Result(now_each / prior_each, f"${now_each:.2f} vs ${prior_each:.2f} a task ({now_each / prior_each:.2f}x)",
                  details=lines)


def probation_rules(text: str) -> list[tuple[str, date]]:
    """(rule, date set) per "Set YYYY-MM-DD (probation)", owned by the nearest heading or bold-lead bullet at or above it."""
    found, owner = [], "(no heading)"
    for line in text.splitlines():
        if RULE_LINE.match(line):
            owner = rule_name(line)
        found += [(owner, date.fromisoformat(day)) for day in PROBATION.findall(line)]
    return found


def fires(rule: str, replies: list[dict] | None) -> str:
    """Reply-check flags that belong to a probation rule; n/a when no feed checks it."""
    feed = next((pattern for key, pattern in PROBATION_FEEDS.items() if key in rule), None)
    if feed is None:
        return "n/a"
    if replies is None:
        return "no data yet"
    return str(sum(bool(re.fullmatch(feed, str(flag))) for rec in replies for flag in rec["flags"]))


def probation_metric(files: list[Path], today: date, replies: list[dict] | None) -> Result:
    rules = [(name, set_on, path.name, (today - set_on).days)
             for path in files for name, set_on in probation_rules(path.read_text(encoding="utf-8"))]
    overdue = [name for name, _, _, age in rules if age > PROBATION_DAYS]
    details = tuple(
        f"{name} ({source}): set {set_on}, {age} day{'' if age == 1 else 's'} old{', overdue' if age > PROBATION_DAYS else ''}; "
        f"check fires in the last {PROBATION_DAYS} days: {fires(name, replies)}"
        for name, set_on, source, age in rules)
    note = "overdue: " + ", ".join(overdue) if overdue else ""
    return Result(len(overdue) / len(rules) if rules else 0.0, f"{len(overdue)} of {len(rules)} overdue", note=note,
                  details=details or ("no probation rules",))


def collect(now: datetime, days: int, fetch: bool) -> dict[str, Result]:
    """Every metric's Result, keyed like GOALS."""
    start = now - timedelta(days=days)
    base = start - timedelta(days=BASELINE_DAYS)
    rows = time_ledger.load_rows(since=stamp(base))
    window, prior = [r for r in rows if r["t0"] >= start], [r for r in rows if r["t0"] < start]
    rule_files = [CLAUDE / "CLAUDE.md", *sorted((CLAUDE / "rules").glob("*.md"))]
    settings = json.loads((CLAUDE / "settings.json").read_text(encoding="utf-8"))
    recent = read_reply_log(REPLY_LOG, now - timedelta(days=PROBATION_DAYS))
    return {
        "approvals": approvals_metric(window, start, days),
        "reply_check": reply_metric(read_reply_log(REPLY_LOG, start)),
        "critical": critical_metric(rule_files, settings, HOOKS),
        "sync": sync_metric(CLAUDE, fetch),
        "evals": eval_metric(CLAUDE / "skills"),
        "spend": spend_metric(window, prior, cost_between(start, None), cost_between(base, start)),
        "probation": probation_metric(rule_files, now.astimezone().date(), recent[0] if recent else None),
    }


PAGE = Template("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Config scorecard $day</title>
<style>
body{font:15px/1.5 "Segoe UI",system-ui,sans-serif;max-width:1040px;margin:32px auto;padding:0 20px;color:#1f2328;background:#fff}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:18px;margin:28px 0 4px}
h3{font-size:15px;margin:16px 0 4px}
.sub,.why,.foot{color:#59636e}
.why{font-size:13px;margin-top:2px}
table{border-collapse:collapse;width:100%;margin-top:16px}
th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #d1d9e0}
th{font-size:13px;font-weight:600}
td.num{white-space:nowrap;font-variant-numeric:tabular-nums}
.nodata{color:#59636e;font-style:italic}
.bar{display:inline-block;width:64px;height:7px;margin-left:8px;border-radius:4px;background:#eaeef2;vertical-align:middle;overflow:hidden}
.bar i{display:block;height:100%}
ul{margin:0;padding-left:20px}
.foot{font-size:13px;margin-top:28px}
</style></head><body>
<h1>Config scorecard: $total/100</h1>
<p class="sub">$window. Seven metrics with equal weight; each scores 0 at its floor and 1 at its target.</p>
<table><tr><th>Metric</th><th>Value</th><th>Target</th><th>Score</th></tr>
$rows
</table>
<h2>Details</h2>
$details
<p class="foot">Written by ~/.claude/scripts/scorecard.py on $day; every run appends a line to ~/.claude/scorecard/history.jsonl.</p>
</body></html>
""")


def bar(value: float) -> str:
    color = "#1a7f37" if value >= 1 else "#bf8700" if value >= 0.5 else "#cf222e"
    return f'<span class="bar"><i style="width:{value:.0%};background:{color}"></i></span>'


def render(scored: list[tuple[Goal, Result, float]], total: float, window: str, day: str) -> str:
    """The self-contained page: one table row per metric, then each metric's detail lines."""
    esc = html.escape
    rows = "\n".join(
        f'<tr><td>{esc(g.name)}<div class="why">{esc(g.why)}</div></td>'
        f'<td class="{"nodata" if r.value is None else "val"}">{esc(r.shown)}</td>'
        f'<td>{esc(goal_text(g))}<div class="why">floor {esc(g.fmt.format(g.floor))}</div></td>'
        f'<td class="num">{s:.2f}{bar(s)}</td></tr>' for g, r, s in scored)
    details = "\n".join(f"<h3>{esc(g.name)}</h3><ul>{''.join(f'<li>{esc(line)}</li>' for line in r.details)}</ul>"
                        for g, r, _ in scored if r.details)
    return PAGE.substitute(day=day, total=f"{total:.0f}", window=esc(window), rows=rows, details=details)


def history(now: datetime, days: int, total: float, scored: list[tuple[Goal, Result, float]]) -> dict:
    metrics = {g.key: {"value": None if r.value is None else round(r.value, 4), "score": round(s, 3)} for g, r, s in scored}
    return {"ts": now.isoformat(), "days": days, "score": round(total, 1), "metrics": metrics}


def main() -> int:
    ap = argparse.ArgumentParser(description="Score the ~/.claude config against its weekly targets.")
    ap.add_argument("--days", type=int, default=7, help="window length in days, ending now")
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch; compare with the last fetched origin/main")
    args = ap.parse_args()
    if sys.stdout:  # None under pythonw, which the weekly task uses
        sys.stdout.reconfigure(errors="replace")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect(now, args.days, fetch=not args.no_fetch)
    scored = [(g, results[g.key], score(results[g.key].value, g.floor, g.target)) for g in GOALS]
    total = overall([s for _, _, s in scored])
    day = now.astimezone().date().isoformat()
    window = f"{args.days} days, {now - timedelta(days=args.days):%Y-%m-%d %H:%M} to {now:%Y-%m-%d %H:%M} UTC"
    OUT.mkdir(parents=True, exist_ok=True)
    page = OUT / f"scorecard-{day}.html"
    page.write_text(render(scored, total, window, day), encoding="utf-8")
    with (OUT / "history.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(history(now, args.days, total, scored)) + "\n")
    print(f"score {total:.0f}/100 over {window}: {page}")
    for g, r, s in scored:
        if s < 1:
            print(f"  {g.name}: {r.shown} (target {goal_text(g)}), score {s:.2f}" + (f"; {r.note}" if r.note else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
