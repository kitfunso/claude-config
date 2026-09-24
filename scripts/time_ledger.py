#!/usr/bin/env python3
"""Where wall-clock goes per human prompt: model thinking, tools, background waits, and stops for approval.

Usage: python time_ledger.py [--since YYYY-MM-DD] [--until ISO] [--skip SESSION_PREFIX] [--stops]
Companion to token_ledger.py, which prices the same transcripts. Main-thread rows only.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
GAP_CAP = 600
APPROVAL = re.compile(
    r"^(yes|y|yep|yeah|ok|okay|go|go ahead|apply|apply consolidated|approved?|proceed|continue|do it|sure|"
    r"confirm(ed)?|ship it|lgtm|carry on|keep going|all of them|both)\b",
    re.I,
)
WAKERS = (
    ("workflow", r"workflow"),
    ("monitor", r"monitor"),
    ("background shell job", r"background command|exit code"),
    ("sub-agent", r"agent"),
)


def when(d: dict) -> datetime:
    return datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))


def text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for b in content or []:
        if b.get("type") == "text":
            parts.append(b.get("text", ""))
        elif b.get("type") == "tool_result":
            c = b.get("content", "")
            parts.append(c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict)))
    return " ".join(parts)


def waker(d: dict) -> str:
    txt = text_of((d.get("message") or {}).get("content"))
    return next((key for key, pat in WAKERS if re.search(pat, txt, re.I)), "other")


def spans(path: Path, since: str, until: str):
    """One span per human prompt: the prompt plus every main-thread row until the next human prompt."""
    cur = None
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not d.get("timestamp") or d.get("isSidechain"):
            continue
        if d["timestamp"] >= until:
            break
        if d.get("type") == "user" and (d.get("origin") or {}).get("kind") == "human":
            if cur:
                yield cur
            fresh = d["timestamp"] >= since
            cur = {"prompt": text_of(d["message"]["content"]).strip(), "start": when(d), "rows": []} if fresh else None
        elif cur is not None:
            cur["rows"].append(d)
    if cur:
        yield cur


def measure(span: dict) -> dict:
    """Model time runs from a request's trigger row to its last block; parked time runs from end_turn to the next user row."""
    prev = end = span["start"]
    reqs: dict[str, dict] = {}
    open_calls: dict[str, tuple] = {}
    tool_secs, parked_by, errors = Counter(), Counter(), []
    active = active_at_reply = stretch = 0.0
    tools, ended, last_text = 0, False, ""
    for d in span["rows"]:
        t, kind = when(d), d.get("type")
        gap = min((t - max(prev, end)).total_seconds(), GAP_CAP) if t > max(prev, end) else 0.0
        active += gap
        stretch += gap if ended else 0.0
        if kind in ("user", "assistant") and stretch:
            parked_by[waker(d) if kind == "user" else "other"] += stretch
            stretch = 0.0
        msg = d.get("message") or {}
        blocks = msg.get("content") if isinstance(msg.get("content"), list) else []
        if kind == "assistant":
            usage = msg.get("usage") or {}
            r = reqs.setdefault(d.get("requestId") or msg.get("id"), {
                "start": prev, "first": t, "kind": blocks[0].get("type") if blocks else "", "out": 0, "think": 0})
            r["end"] = t
            r["out"] = max(r["out"], usage.get("output_tokens", 0))
            r["think"] = max(r["think"], (usage.get("output_tokens_details") or {}).get("thinking_tokens", 0))
            for b in blocks:
                if b.get("type") == "text" and b.get("text", "").strip():
                    last_text = b["text"]
                if b.get("type") == "tool_use":
                    tools += 1
                    open_calls[b.get("id")] = (b.get("name", "?"), t)
            end, ended, active_at_reply = t, msg.get("stop_reason") == "end_turn", active
            continue
        prev, ended = t, ended and kind != "user"
        for b in blocks if kind == "user" else []:
            if b.get("type") == "tool_result":
                errors += [text_of([b])[:90]] if b.get("is_error") else []
                if b.get("tool_use_id") in open_calls:
                    name, t0 = open_calls.pop(b["tool_use_id"])
                    tool_secs[name] += (t - t0).total_seconds()
    return {
        "prompt": span["prompt"], "t0": span["start"], "t1": end, "secs": (end - span["start"]).total_seconds(),
        "active": active_at_reply, "model": sum((r["end"] - r["start"]).total_seconds() for r in reqs.values()),
        "think_wait": sum((r["first"] - r["start"]).total_seconds() for r in reqs.values() if r["kind"] == "thinking"),
        "requests": len(reqs), "tools": tools, "out": sum(r["out"] for r in reqs.values()),
        "think": sum(r["think"] for r in reqs.values()), "errors": errors, "last_text": last_text,
        "parked_by": parked_by, "tool_secs": tool_secs,
    }


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(int(q * len(xs)), len(xs) - 1)] if xs else 0.0


def hours(c: Counter, n: int = 8) -> list:
    return [(k, round(v / 3600, 1)) for k, v in c.most_common(n)]


def stops(rows: list[dict], show: bool) -> None:
    gaps = []
    for prev, r in zip(rows, rows[1:]):
        if prev["session"] == r["session"] and len(r["prompt"]) <= 60 and APPROVAL.match(r["prompt"]):
            gaps.append((r["t0"] - prev["t1"]).total_seconds() / 60)
            if show:
                tail = " ".join(prev["last_text"].split())[-160:]
                print(f"  {gaps[-1]:6.1f} min [{r['prompt'][:22]!r}] <- ...{tail}")
    capped = sum(min(g, 60) for g in gaps) / 60
    print(f"approval-only replies {len(gaps)} of {len(rows)} prompts: idle median {statistics.median(gaps) if gaps else 0:.1f} min, "
          f"total {sum(gaps) / 60:.1f} h, {capped:.1f} h with each stop capped at 60 min")


def report(rows: list[dict], show_stops: bool) -> None:
    tasks = [r for r in rows if r["tools"] > 0]
    act = max(sum(r["active"] for r in rows), 1.0)
    model, think_wait = sum(r["model"] for r in rows), sum(r["think_wait"] for r in rows)
    out, think, reqs = sum(r["out"] for r in rows), sum(r["think"] for r in rows), sum(r["requests"] for r in rows)
    parked = sum((r["parked_by"] for r in rows), Counter())
    tool_secs = sum((r["tool_secs"] for r in rows), Counter())
    mins = [r["secs"] / 60 for r in tasks] or [0.0]
    print(f"sessions {len({r['session'] for r in rows})}  prompts {len(rows)}  with tools {len(tasks)}  requests {reqs:,}")
    print(f"task minutes: median {statistics.median(mins):.1f}  p75 {pct(mins, .75):.1f}  p90 {pct(mins, .9):.1f}")
    print(f"working time {act / 3600:.1f} h (gaps capped at {GAP_CAP // 60} min, each prompt ends at its last reply)")
    print(f"  model {model / act:.0%}, of which silent thinking before first output {think_wait / act:.0%}")
    print(f"  parked on background work {sum(parked.values()) / act:.0%}: {hours(parked)}")
    print(f"  foreground tools {sum(tool_secs.values()) / act:.0%} (parallel calls overlap): {hours(tool_secs)}")
    print(f"output tokens {out:,}: thinking {think / max(out, 1):.0%}, {think / max(reqs, 1):,.0f} per request")
    stops(rows, show_stops)
    errs = Counter(re.sub(r"\d+", "N", e[:55]) for r in rows for e in r["errors"])
    hooks = sum(n for e, n in errs.items() if re.search(r"hook error|ps-stderr-guard", e, re.I))
    print(f"tool errors {sum(errs.values())}, hook denials {hooks}; top: {errs.most_common(5)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="")
    ap.add_argument("--until", default="9999")
    ap.add_argument("--skip", default="")
    ap.add_argument("--stops", action="store_true", help="print what the last reply said before each approval-only prompt")
    args = ap.parse_args()
    rows = []
    for path in sorted(PROJECTS.glob("*/*.jsonl")):
        if not (args.skip and path.stem.startswith(args.skip)):
            rows += [dict(measure(s), session=path.stem[:8]) for s in spans(path, args.since, args.until)]
    report(rows, args.stops)


if __name__ == "__main__":
    main()
