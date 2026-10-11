"""Sub-agent burn: per agent file, joined to its .meta.json, plus cwd-based project attribution."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from token_burn import CUTOFF, ROOT, W_MODEL, family, parse_ts, split_usage, weight


def project_of(cwd: str) -> str:
    m = re.search(r"skf_s[\\/]+([^\\/]+)", cwd or "")
    name = m.group(1) if m else "(home)"
    return re.sub(r"-wt-.*$|-archive$", "", name) if name.startswith("hippo") else name


def load(path: Path) -> list[dict]:
    calls: dict[str, dict] = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = parse_ts(rec.get("timestamp"))
            msg = rec.get("message") or {}
            usage = msg.get("usage")
            model = msg.get("model") or ""
            if rec.get("type") != "assistant" or not usage or ts is None or ts < CUTOFF or model.startswith("<"):
                continue
            key = rec.get("requestId") or msg.get("id") or rec.get("uuid")
            calls[key] = {"ts": ts, "model": family(model), "cwd": rec.get("cwd") or "", **split_usage(usage)}
    return sorted(calls.values(), key=lambda c: c["ts"])


def ctx(c: dict) -> int:
    return c["in"] + c["cw5m"] + c["cw1h"] + c["cr"]


def show(title: str, rows: dict[str, float], total: float, top: int = 14) -> None:
    print(f"\n## {title}")
    for name, val in sorted(rows.items(), key=lambda kv: -kv[1])[:top]:
        print(f"  {val / total * 100:5.1f}%  {name}")


def main() -> None:
    files = [p for p in ROOT.rglob("*.jsonl") if p.stat().st_mtime >= CUTOFF.timestamp()]
    total = 0.0
    by: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    agents: list[dict] = []
    type_n: Counter[str] = Counter()
    for path in files:
        calls = load(path)
        if not calls:
            continue
        w = sum(weight(c) for c in calls)
        total += w
        sub = "subagents" in path.parts or path.name.startswith("agent-")
        proj = project_of(Counter(c["cwd"] for c in calls).most_common(1)[0][0])
        by["project by cwd (main + sub)"][proj] += w
        if not sub:
            continue
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        kind = meta.get("agentType") or ("workflow" if "workflows" in path.parts else "unknown")
        model = calls[0]["model"]
        rest = sum(weight(c) for c in calls[1:])
        agents.append({"w": w, "n": len(calls), "first": ctx(calls[0]), "peak": max(ctx(c) for c in calls),
                       "kind": kind, "model": model, "desc": meta.get("description", ""), "proj": proj})
        by["sub-agent type"][kind] += w
        by["sub-agent model"][model] += w
        by["sub-agent project"][proj] += w
        type_n[kind] += 1
        size = "1-10 calls" if len(calls) <= 10 else "11-40" if len(calls) <= 40 else "41-100" if len(calls) <= 100 else "100+ calls"
        by["sub-agent length"][size] += w
        by["sub-agent first call vs the rest"]["first call (the brief + config floor)"] += w - rest
        by["sub-agent first call vs the rest"]["later calls (re-reading its own history)"] += rest
        for c in calls:
            m = W_MODEL.get(c["model"], 0.4)
            by["sub-agent token type"]["cache read"] += c["cr"] * 0.1 * m
            by["sub-agent token type"]["cache write"] += (c["cw5m"] * 1.25 + c["cw1h"] * 2.0) * m
            by["sub-agent token type"]["output"] += c["out"] * 5.0 * m

    sub_total = sum(a["w"] for a in agents)
    print(f"agents: {len(agents):,} | sub-agent share of all burn: {sub_total / total * 100:.1f}%")
    ns = sorted(a["n"] for a in agents)
    firsts = sorted(a["first"] for a in agents)
    peaks = sorted(a["peak"] for a in agents)
    mid = len(agents) // 2
    print(f"median calls per agent {ns[mid]} | p90 {ns[int(len(ns) * 0.9)]} | max {ns[-1]}")
    print(f"median first-call context {firsts[mid] / 1e3:.0f}k | median peak {peaks[mid] / 1e3:.0f}k | p90 peak {peaks[int(len(peaks) * 0.9)] / 1e3:.0f}k")
    show("project by cwd (main + sub), share of ALL burn", by["project by cwd (main + sub)"], total)
    for title in ("sub-agent type", "sub-agent model", "sub-agent length", "sub-agent first call vs the rest",
                  "sub-agent token type", "sub-agent project"):
        show(f"{title}, share of sub-agent burn", by[title], sub_total)
    print("\n## agent count by type")
    for kind, n in type_n.most_common(14):
        print(f"  {n:5d}  {kind}")
    print("\n## 15 costliest agents: share of ALL burn | calls | first ctx | peak ctx | model | type | description")
    for a in sorted(agents, key=lambda a: -a["w"])[:15]:
        print(f"  {a['w'] / total * 100:4.1f}%  {a['n']:4d}  {a['first'] / 1e3:4.0f}k  {a['peak'] / 1e3:4.0f}k  {a['model']:6s} {a['kind']:22s} {a['proj']:12s} {a['desc'][:60]}")


if __name__ == "__main__":
    main()
