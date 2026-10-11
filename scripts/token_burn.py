"""Where the tokens went: aggregate usage from Claude Code transcripts, deduped by API request."""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
CUTOFF = datetime.now(timezone.utc) - timedelta(days=DAYS)
# Relative weights: input=1, per the price ratios stated in ~/.claude/CLAUDE.md Model Routing.
W_TYPE = {"in": 1.0, "cw5m": 1.25, "cw1h": 2.0, "cr": 0.1, "out": 5.0}
W_MODEL = {"fable": 1.0, "opus": 0.4, "sonnet": 0.2, "haiku": 0.07}


def family(model: str) -> str:
    for name in W_MODEL:
        if name in model:
            return name
    return "other"


def parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def split_usage(usage: dict) -> dict[str, int]:
    cc = usage.get("cache_creation") or {}
    cw_total = usage.get("cache_creation_input_tokens") or 0
    cw1h = cc.get("ephemeral_1h_input_tokens") or 0
    cw5m = cc.get("ephemeral_5m_input_tokens") or (cw_total - cw1h)
    return {
        "in": usage.get("input_tokens") or 0,
        "cw5m": max(cw5m, 0),
        "cw1h": cw1h,
        "cr": usage.get("cache_read_input_tokens") or 0,
        "out": usage.get("output_tokens") or 0,
    }


def main() -> None:
    calls: dict[str, dict] = {}
    tools_main: Counter[str] = Counter()
    seen_tools: set[str] = set()
    prompts: Counter[str] = Counter()
    files = [p for p in ROOT.rglob("*.jsonl") if p.stat().st_mtime >= CUTOFF.timestamp()]
    for path in files:
        rel = path.relative_to(ROOT)
        project = rel.parts[0]
        sub = "subagents" in rel.parts or path.name.startswith("agent-")
        session = rel.parts[1].replace(".jsonl", "") if len(rel.parts) > 1 else path.stem
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = parse_ts(rec.get("timestamp"))
                if ts is None or ts < CUTOFF:
                    continue
                side = sub or bool(rec.get("isSidechain"))
                msg = rec.get("message") or {}
                if rec.get("type") == "user" and not side:
                    content = msg.get("content")
                    is_tool = isinstance(content, list) and any(
                        isinstance(b, dict) and b.get("type") == "tool_result" for b in content
                    )
                    if not is_tool and not rec.get("isMeta"):
                        prompts[session] += 1
                    continue
                if rec.get("type") != "assistant":
                    continue
                usage = msg.get("usage")
                model = msg.get("model") or ""
                if not usage or model.startswith("<"):
                    continue
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tid = block.get("id") or ""
                        if tid not in seen_tools:
                            seen_tools.add(tid)
                            if not side:
                                tools_main[block.get("name") or "?"] += 1
                key = rec.get("requestId") or msg.get("id") or rec.get("uuid")
                calls[key] = {
                    "ts": ts, "model": family(model), "project": project,
                    "session": session, "side": side, **split_usage(usage),
                }
    report(list(calls.values()), tools_main, prompts, len(files))


def weight(c: dict) -> float:
    return W_MODEL.get(c["model"], 0.4) * sum(c[k] * w for k, w in W_TYPE.items())


def table(title: str, rows: dict[str, float], total: float, top: int = 12) -> None:
    print(f"\n## {title}")
    for name, val in sorted(rows.items(), key=lambda kv: -kv[1])[:top]:
        print(f"  {val / total * 100:5.1f}%  {name}")


def report(calls: list[dict], tools_main: Counter[str], prompts: Counter[str], nfiles: int) -> None:
    total = sum(weight(c) for c in calls)
    raw = {k: sum(c[k] for c in calls) for k in W_TYPE}
    print(f"window: last {DAYS} days | files {nfiles} | API calls {len(calls):,}")
    print("raw tokens: " + " | ".join(f"{k} {v / 1e6:,.1f}M" for k, v in raw.items()))

    by: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    sess_calls: Counter[str] = Counter()
    sess_ctx: dict[str, int] = defaultdict(int)
    cold = 0.0
    buckets: dict[str, float] = defaultdict(float)
    bucket_n: Counter[str] = Counter()
    for c in calls:
        w = weight(c)
        m = W_MODEL.get(c["model"], 0.4)
        for k, wt in W_TYPE.items():
            by["token type (weighted)"][k] += c[k] * wt * m
        by["model"][c["model"]] += w
        by["thread"]["sub-agent" if c["side"] else "main thread"] += w
        by["project"][c["project"]] += w
        by["day"][c["ts"].strftime("%Y-%m-%d")] += w
        ctx = c["in"] + c["cw5m"] + c["cw1h"] + c["cr"]
        if not c["side"]:
            tag = f"{c['session'][:8]} {c['model']} {c['project'][-28:]}"
            by["session (main thread)"][tag] += w
            sess_calls[tag] += 1
            sess_ctx[tag] += ctx
        b = "<50k" if ctx < 5e4 else "50-100k" if ctx < 1e5 else "100-200k" if ctx < 2e5 else "200k+"
        buckets[b] += w
        bucket_n[b] += 1
        if ctx > 3e4 and c["cr"] < 0.5 * ctx:
            cold += (c["cw5m"] * 1.25 + c["cw1h"] * 2.0) * m

    for title in ("token type (weighted)", "model", "thread", "project"):
        table(title, by[title], total)
    print("\n## context size per call: share of burn (share of calls)")
    for b in ("<50k", "50-100k", "100-200k", "200k+"):
        print(f"  {buckets[b] / total * 100:5.1f}%  ({bucket_n[b] / len(calls) * 100:4.1f}% of calls)  {b}")
    print(f"\n## cold cache rewrites (context >30k, under half read from cache): {cold / total * 100:.1f}% of burn")
    print("\n## top main-thread sessions: share | calls | mean ctx | prompts")
    top = sorted(by["session (main thread)"].items(), key=lambda kv: -kv[1])[:12]
    for tag, w in top:
        n = sess_calls[tag]
        sid = tag.split()[0]
        np_ = sum(v for k, v in prompts.items() if k.startswith(sid))
        print(f"  {w / total * 100:5.1f}%  {n:5d}  {sess_ctx[tag] / n / 1e3:6.0f}k  {np_:4d}  {tag}")
    print(f"  top-12 total: {sum(w for _, w in top) / total * 100:.1f}% of all burn; main sessions: {len(sess_calls)}")
    table("day", dict(sorted(by["day"].items())), total, top=40)
    tt = sum(tools_main.values())
    print(f"\n## main-thread tool calls: {tt:,}")
    for name, n in tools_main.most_common(12):
        print(f"  {n / tt * 100:5.1f}%  {n:6d}  {name}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"\n({time.time() - t0:.0f}s)")
