"""One self-contained HTML page from a prune-tests run folder; missing stages show as not run."""
from __future__ import annotations

import html
from pathlib import Path

import runner

CSS = """body{font:15px/1.5 system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#222}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:1.6rem}table{border-collapse:collapse;width:100%;font-size:13px}
td,th{border-bottom:1px solid #ddd;padding:3px 6px;text-align:left;vertical-align:top}
code{font-size:12px}.bad{color:#b00020}.ok{color:#0a7a3d}details{margin:.4rem 0}summary{cursor:pointer}"""


def _opt(d: Path, name: str) -> dict | None:
    return runner.read_json(d / name) if (d / name).exists() else None


def _e(x) -> str:
    return html.escape(str(x))


def _code(xs) -> str:
    return "<br>".join(f"<code>{_e(x)}</code>" for x in xs)


def _table(head: list[str], rows: list[list]) -> str:
    th = "".join(f"<th>{_e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{body}</table>"


def _fold(title: str, inner: str) -> str:
    return f"<details><summary>{_e(title)}</summary>{inner}</details>"


def _timing_line(label: str, before: dict | None, after: dict | None) -> str:
    if not before:
        return f"<p>{_e(label)}: not measured.</p>"
    if not after:
        return (f"<p><b>{_e(label)}:</b> {before['median_wall']:.0f}s before "
                f"({before['n_collected']} tests); after not measured.</p>")
    return (f"<p><b>{_e(label)}: {before['median_wall']:.0f}s to {after['median_wall']:.0f}s</b> "
            f"(median of {len(after['walls'])} runs; {before['n_collected']} to {after['n_collected']} tests)</p>")


def _profile(prof: dict, heavy: list[str]) -> str:
    dur = prof["tests"]
    total = sum(dur.values()) or 1.0
    top = sorted(dur.items(), key=lambda kv: -kv[1])[:15]
    rows = [[f"<code>{_e(t)}</code>", f"{s:.1f}s", f"{100 * s / total:.0f}%", "heavy" if t in heavy else ""]
            for t, s in top]
    overhead = max(prof["median_wall"] - total, 0)
    return (f"<p>Collection alone {prof['collect_s']:.0f}s; test time {total:.0f}s; start-up and collection "
            f"inside a run about {overhead:.0f}s. The 15 slowest tests take "
            f"{100 * sum(s for _, s in top) / total:.0f}% of test time; {len(heavy)} tests are heavy.</p>"
            + _fold("Slowest tests", _table(["test", "time", "share", ""], rows)))


def _checks(ver: dict | None, rep: dict | None) -> list[str]:
    out = []
    if ver:
        cls = "ok" if not ver["lost"] else "bad"
        out.append(f"<p class='{cls}'><b>Planted-bug check: {ver['checked']} bugs a cut test caught were "
                   f"re-planted on the slim branch; {len(ver['lost'])} lost.</b></p>")
    if rep:
        rows = rep["rows"]
        lost = sum(r["verdict"] == "lost" for r in rows)
        full = sum(r["verdict"] in ("caught", "lost") for r in rows)
        cls = "ok" if not lost else "bad"
        out.append(f"<p class='{cls}'><b>Past-bug replay: the full suite caught {full} of {len(rows)} replayed "
                   f"fix commits; the slim suite lost {lost}.</b></p>")
    return out


def write_report(d: Path, out: Path) -> None:
    pb, pa = _opt(d, "profile-before.json"), _opt(d, "profile-after.json")
    cb, ca = _opt(d, "change-before.json"), _opt(d, "change-after.json")
    cand, plan = _opt(d, "candidates.json"), _opt(d, "plan.json")
    ver, rep = _opt(d, "verify.json"), _opt(d, "replay.json")
    parts = [f"<h1>prune-tests: {_e(d.name)}</h1>", _timing_line("Full run", pb, pa),
             _timing_line("Per-change run", cb, ca), *_checks(ver, rep)]
    if pb:
        parts += ["<h2>Where the minutes go</h2>", _profile(pb, plan["heavy"] if plan else [])]
    if plan:
        sampled = " Mutants were sampled, so each cut rests on part of the evidence." if plan["sampled"] else ""
        parts += ["<h2>Cuts</h2>",
                  f"<p>{len(plan['cut'])} tests cut; {len(plan['kept'])} overlapping tests kept because only they "
                  f"catch a planted bug. {plan['survivors']} planted bugs no candidate caught; "
                  f"{plan['unsure_keeper_runs']} keeper runs hit the time budget, so their candidates stayed."
                  f"{sampled}</p>",
                  _fold("Cut ledger", _table(["test", "reason", "now caught by"], [
                      [_code([r["test"]]), _e(r["reason"]), _code(r["caught_by"])] for r in plan["cut"]])),
                  _fold("Kept for a unique catch", _table(["test", "bugs only candidates catch"], [
                      [_code([r["test"]]), r["bugs_only_candidates_catch"]] for r in plan["kept"]]))]
    if cand:
        parts.append(_fold(f"Exempt ({len(cand['exempt'])}) and no-coverage ({len(cand['no_coverage'])}) tests",
                           _table(["test", "list"], [[_code([t]), "exempt"] for t in cand["exempt"]]
                                  + [[_code([t]), "no coverage"] for t in cand["no_coverage"]])))
    if ver and ver["lost"]:
        parts.append(_fold("Lost planted bugs", _table(["mutant", "change"],
                                                       [[_e(r["id"]), _e(r["desc"])] for r in ver["lost"]])))
    if rep:
        parts.append(_fold("Replay rows", _table(["commit", "subject", "verdict", "cut tests that failed"], [
            [_e(r["sha"][:8]), _e(r["subject"]), _e(r["verdict"]), _code(r.get("cut_failed", []))]
            for r in rep["rows"]])))
    out.write_text(f"<!doctype html><meta charset='utf-8'><title>prune-tests</title><style>{CSS}</style>\n"
                   + "\n".join(parts), encoding="utf-8")
    print(f"wrote {out}")
