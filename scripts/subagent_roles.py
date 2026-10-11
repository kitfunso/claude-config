"""Who the sub-agents are: orchestrator, critic or leaf, by model; batching; tools each type really uses."""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.argv = [sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else "14"]
from token_burn import CUTOFF, ROOT, W_MODEL, family, parse_ts, split_usage, weight  # noqa: E402

CRITIC = re.compile(r"critic|critique|review|score |audit|verify|grill|judge|red.?team", re.I)
READISH = {"Read", "Grep", "Glob"}
SHELL_READ = re.compile(r"^\s*(cd \S+ && )?(sed -n|cat |grep |rg |ls |wc |head |tail |git (-C \S+ )?(log|show|diff|status|branch))")


def read(path: Path) -> list[dict]:
    calls: dict[str, dict] = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = parse_ts(rec.get("timestamp"))
            msg = rec.get("message") or {}
            usage, model = msg.get("usage"), msg.get("model") or ""
            if rec.get("type") != "assistant" or ts is None or ts < CUTOFF or not usage or model.startswith("<"):
                continue
            key = rec.get("requestId") or msg.get("id") or rec.get("uuid")
            call = calls.setdefault(key, {"ts": ts, "model": family(model), "tools": [], **split_usage(usage)})
            for b in msg.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    name = b.get("name", "?")
                    cmd = (b.get("input") or {}).get("command", "") if name in ("Bash", "PowerShell") else ""
                    call["tools"].append((name, bool(cmd and SHELL_READ.match(cmd))))
    return sorted(calls.values(), key=lambda c: c["ts"])


def ctx(c: dict) -> int:
    return c["in"] + c["cw5m"] + c["cw1h"] + c["cr"]


def readish(call: dict) -> bool:
    return len(call["tools"]) == 1 and (call["tools"][0][0] in READISH or call["tools"][0][1])


def main() -> None:
    total = 0.0
    role_w: dict[str, float] = defaultdict(float)
    role_n: Counter[str] = Counter()
    role_calls: dict[str, list[int]] = defaultdict(list)
    role_ctx: dict[str, list[float]] = defaultdict(list)
    tools_by_type: dict[str, Counter[str]] = defaultdict(Counter)
    orch_tools: Counter[str] = Counter()
    batch: dict[str, Counter[str]] = {"main": Counter(), "sub": Counter()}
    chain_w: dict[str, float] = defaultdict(float)
    side_w: dict[str, float] = defaultdict(float)
    for path in ROOT.rglob("*.jsonl"):
        if path.stat().st_mtime < CUTOFF.timestamp():
            continue
        calls = read(path)
        if not calls:
            continue
        w = sum(weight(c) for c in calls)
        total += w
        is_sub = "subagents" in path.parts
        side = "sub" if is_sub else "main"
        side_w[side] += w
        for i, c in enumerate(calls):
            if not c["tools"]:
                continue
            batch[side]["tool calls"] += 1
            batch[side]["tools"] += len(c["tools"])
            batch[side]["single"] += len(c["tools"]) == 1
            if i and readish(c) and readish(calls[i - 1]):
                batch[side]["chained single reads"] += 1
                chain_w[side] += weight(c)
        if not is_sub:
            continue
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        kind, desc = meta.get("agentType", "?"), meta.get("description", "")
        names = Counter(t[0] for c in calls for t in c["tools"])
        spawns = names.get("Agent", 0)
        if spawns >= 2:
            role = "orchestrator (spawns its own agents)"
            orch_tools.update(names)
        elif kind == "senior-code-reviewer" or CRITIC.search(desc):
            role = "critic / reviewer"
        else:
            role = "leaf worker (builds or researches)"
        key = f"{role} | {calls[0]['model']}"
        role_w[key] += w
        role_n[key] += 1
        role_calls[key].append(len(calls))
        role_ctx[key].append(sum(ctx(c) for c in calls) / len(calls))
        tools_by_type[kind].update(names)

    print("## sub-agent roles: share of ALL burn | agents | median calls | p90 calls | mean ctx")
    for key, w in sorted(role_w.items(), key=lambda kv: -kv[1]):
        n = sorted(role_calls[key])
        print(f"  {w / total * 100:5.1f}%  {role_n[key]:4d}  {st.median(n):5.0f}  {n[int(len(n) * 0.9)]:5d}  {st.mean(role_ctx[key]) / 1e3:5.0f}k  {key}")

    tot = sum(orch_tools.values())
    print(f"\n## what orchestrator sub-agents call themselves ({tot:,} tool calls)")
    print("  " + ", ".join(f"{k} {v / tot * 100:.0f}%" for k, v in orch_tools.most_common(9)))

    print("\n## batching")
    for side in ("main", "sub"):
        b = batch[side]
        print(f"  {side}: {b['tools'] / b['tool calls']:.2f} tools per tool-using call | {b['single'] / b['tool calls'] * 100:.0f}% carry one tool | "
              f"chained single reads {b['chained single reads']:,} calls = {chain_w[side] / total * 100:.1f}% of ALL burn")

    print("\n## tools each custom type used (count)")
    for kind in ("typescript-pro", "senior-code-reviewer", "debugger", "frontend-developer", "python-backend-engineer", "general-purpose", "worker"):
        c = tools_by_type.get(kind)
        if c:
            print(f"  {kind}: " + ", ".join(f"{k} {v}" for k, v in c.most_common(16)))


if __name__ == "__main__":
    main()
