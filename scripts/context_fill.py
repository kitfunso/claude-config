"""What fills context (tool result sizes by tool and command) and why cache gets rewritten."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from token_burn import CUTOFF, ROOT, W_MODEL, family, parse_ts, split_usage, weight


def size_of(content: object) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(b.get("text") or "") for b in content if isinstance(b, dict))
    return 0


def cmd_head(command: str) -> str:
    words = re.sub(r'^(cd\s+\S+\s*&&\s*)', "", command.strip()).split()
    head = " ".join(words[:2]) if words else "?"
    return re.sub(r'["\']?[A-Za-z]:[\\/]\S*|/\S+', "<path>", head)[:40]


def main() -> None:
    chars: dict[str, Counter[str]] = {"main": Counter(), "sub": Counter()}
    count: dict[str, Counter[str]] = {"main": Counter(), "sub": Counter()}
    bash: Counter[str] = Counter()
    bash_n: Counter[str] = Counter()
    big: Counter[str] = Counter()
    rewrite: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    total = 0.0
    for path in ROOT.rglob("*.jsonl"):
        if path.stat().st_mtime < CUTOFF.timestamp():
            continue
        side = "sub" if ("subagents" in path.parts or path.name.startswith("agent-")) else "main"
        names: dict[str, str] = {}
        cmds: dict[str, str] = {}
        calls: dict[str, dict] = {}
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = parse_ts(rec.get("timestamp"))
                if ts is None or ts < CUTOFF:
                    continue
                msg = rec.get("message") or {}
                content = msg.get("content")
                if rec.get("type") == "assistant":
                    for b in content or []:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            names[b.get("id", "")] = b.get("name", "?")
                            if b.get("name") in ("Bash", "PowerShell"):
                                cmds[b.get("id", "")] = cmd_head((b.get("input") or {}).get("command", ""))
                    usage = msg.get("usage")
                    model = msg.get("model") or ""
                    if usage and not model.startswith("<"):
                        key = rec.get("requestId") or msg.get("id") or rec.get("uuid")
                        calls[key] = {"ts": ts, "model": family(model), **split_usage(usage)}
                elif rec.get("type") == "user" and isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            tid = b.get("tool_use_id", "")
                            n = size_of(b.get("content"))
                            name = names.get(tid, "?")
                            name = "mcp:browser" if "chrome" in name or "playwright" in name else name
                            chars[side][name] += n
                            count[side][name] += 1
                            if tid in cmds:
                                bash[cmds[tid]] += n
                                bash_n[cmds[tid]] += 1
                            if n > 20000:
                                big[name] += n
        ordered = sorted(calls.values(), key=lambda c: c["ts"])
        prev = None
        for c in ordered:
            w = weight(c)
            total += w
            m = W_MODEL.get(c["model"], 0.4)
            cw = (c["cw5m"] * 1.25 + c["cw1h"] * 2.0) * m
            ctx = c["in"] + c["cw5m"] + c["cw1h"] + c["cr"]
            gap = (c["ts"] - prev).total_seconds() if prev else 0.0
            prev = c["ts"]
            if ctx > 3e4 and c["cr"] < 0.5 * ctx:
                why = "first call" if gap == 0.0 else "idle >60 min" if gap > 3600 else "idle 5-60 min" if gap > 300 else "no idle gap (compaction or cache break)"
                rewrite[side][f"COLD {why}"] += cw
            else:
                rewrite[side]["normal incremental write"] += cw

    print("## cache-write cost by cause, share of ALL burn")
    for side in ("main", "sub"):
        for why, v in sorted(rewrite[side].items(), key=lambda kv: -kv[1]):
            print(f"  {v / total * 100:5.1f}%  {side:4s} {why}")
    for side in ("main", "sub"):
        tot = sum(chars[side].values())
        print(f"\n## {side}: tool-result text entering context, {tot / 1e6:,.0f}M chars")
        for name, n in chars[side].most_common(9):
            print(f"  {n / tot * 100:5.1f}%  {count[side][name]:6d} calls  mean {n / count[side][name]:7,.0f} chars  {name}")
    tot_b = sum(bash.values())
    print(f"\n## shell commands by output volume ({tot_b / 1e6:,.0f}M chars)")
    for head, n in bash.most_common(18):
        print(f"  {n / tot_b * 100:5.1f}%  {bash_n[head]:6d} calls  mean {n / bash_n[head]:7,.0f} chars  {head}")
    all_chars = sum(sum(c.values()) for c in chars.values())
    print(f"\n## results over 20k chars: {sum(big.values()) / all_chars * 100:.1f}% of all tool-result text")
    for name, n in big.most_common(6):
        print(f"  {n / all_chars * 100:5.1f}%  {name}")


if __name__ == "__main__":
    main()
