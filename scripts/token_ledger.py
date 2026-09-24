#!/usr/bin/env python3
"""Price every Claude Code request under ~/.claude/projects by billing type and by what filled the prompt.

Usage: python token_ledger.py [--since YYYY-MM-DD] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
CHARS_PER_TOKEN = 4.0
# $ per MTok: input, output, cache read, 5m write, 1h write. Most specific key first.
PRICES = {
    "opus-5-5": (4.0, 20.0, 0.20, 5.0, 8.0),
    "opus": (5.0, 25.0, 0.50, 6.25, 10.0),
    "sonnet-5": (2.0, 10.0, 0.20, 2.5, 4.0),
    "sonnet": (3.0, 15.0, 0.30, 3.75, 6.0),
    "fable-5-1": (10.0, 50.0, 0.25, 12.5, 20.0),
    "fable": (10.0, 50.0, 1.00, 12.5, 20.0),
    "haiku": (1.0, 5.0, 0.10, 1.25, 2.0),
}
NOT_SENT = {"prompt_snapshot", "deferred_tools_record", "thinking_drop"}
ATTACH_SOURCE = {
    "instructions": "setup: CLAUDE.md + rules + memory",
    "nested_memory": "setup: CLAUDE.md + rules + memory",
    "skill_listing": "setup: skill listing",
    "deferred_tools_delta": "setup: tool/agent/MCP listings",
    "agent_listing_delta": "setup: tool/agent/MCP listings",
    "mcp_instructions_delta": "setup: tool/agent/MCP listings",
    "invoked_skills": "skill bodies",
    "file": "files attached",
    "edited_text_file": "files attached",
    "compact_file_reference": "files attached",
    "queued_command": "user prompts",
}


def price(model: str) -> tuple[float, ...] | None:
    return next((p for key, p in PRICES.items() if key in model), None)


def text_len(content: object) -> int:
    return len(content) if isinstance(content, str) else len(json.dumps(content, ensure_ascii=False))


@dataclass
class Ledger:
    cost: Counter = field(default_factory=Counter)  # (source, billing) -> $
    tokens: Counter = field(default_factory=Counter)  # (source, billing) -> tokens
    by_who: Counter = field(default_factory=Counter)  # (who, billing) -> $
    by_model: Counter = field(default_factory=Counter)
    tool_calls: Counter = field(default_factory=Counter)
    tool_errors: Counter = field(default_factory=Counter)
    tool_sessions: dict = field(default_factory=lambda: defaultdict(set))
    sessions: dict = field(default_factory=lambda: defaultdict(Counter))
    first_prefix: list = field(default_factory=list)
    cold: list = field(default_factory=list)
    compactions: list = field(default_factory=list)
    billed: float = 0.0


def attachment_item(a: dict) -> tuple[str, int] | None:
    kind = a.get("type", "")
    if kind in NOT_SENT:
        return None
    if kind in ("hook_success", "hook_additional_context"):
        event = a.get("hookEvent") or str(a.get("hookName", "")).split(":")[0]
        if kind == "hook_success" and event not in ("SessionStart", "UserPromptSubmit"):
            return None
        return f"hooks: {event}", text_len(a.get("content", ""))
    return ATTACH_SOURCE.get(kind, "harness reminders"), text_len(a)


def user_items(d: dict, tool_names: dict) -> list[tuple[str, int]]:
    content = d["message"]["content"]
    if d.get("isCompactSummary"):
        return [("compaction summary", text_len(content))]
    if d.get("isMeta"):
        return [("skill bodies", text_len(content))]
    if isinstance(content, str):
        return [("user prompts", len(content))]
    items = []
    for block in content:
        if block.get("type") == "tool_result":
            items.append((f"tool: {tool_names.get(block.get('tool_use_id'), '?')}", text_len(block.get("content", ""))))
        else:
            items.append(("user prompts", text_len(block)))
    return items


def charge(ledger: Ledger, items: list, usage: dict, p: tuple, who: str) -> float:
    """Tail tokens are uncached, then written, the rest read: walk items newest first."""
    inp, cc, cr = usage["input_tokens"], usage["cache_creation_input_tokens"], usage["cache_read_input_tokens"]
    split = usage.get("cache_creation") or {}
    w1h = split.get("ephemeral_1h_input_tokens", 0)
    write_rate = ((cc - w1h) * p[3] + w1h * p[4]) / cc if cc else p[3]
    scale = (inp + cc + cr) / max(sum(t for _, t in items), 1)
    budget = [("uncached input", inp, p[0]), ("cache write", cc, write_rate), ("cache read", cr, p[2])]
    total = 0.0
    for source, tok in reversed(items):
        tok *= scale
        while tok > 1e-9 and budget:
            billing, left, rate = budget[0]
            take = min(tok, left)
            dollars = take * rate / 1e6
            ledger.cost[(source, billing)] += dollars
            ledger.tokens[(source, billing)] += take
            ledger.by_who[(who, billing)] += dollars
            total += dollars
            tok -= take
            budget[0] = (billing, left - take, rate)
            if budget[0][1] <= 1e-9:
                budget.pop(0)
    return total


def final_output(path: Path) -> dict[str, tuple[int, int]]:
    """(output, thinking) per request: subagent transcripts log partial counts on a request's first entry."""
    final: dict[str, tuple[int, int]] = {}
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        msg = d.get("message") or {}
        usage, rid = msg.get("usage"), d.get("requestId") or msg.get("id")
        if d.get("type") == "assistant" and usage and rid:
            now = (usage["output_tokens"], (usage.get("output_tokens_details") or {}).get("thinking_tokens", 0))
            final[rid] = max(final.get(rid, (0, 0)), now)
    return final


def walk(path: Path, ledger: Ledger, since: str, session: str, who: str) -> None:
    final = final_output(path)
    tool_names: dict[str, str] = {}
    items: list[list] = []
    pending: list[tuple[str, int]] = []
    seen: set[str] = set()
    prev_prefix = prev_out = 0
    prev_ts = ""
    model = ""
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        kind = d.get("type")
        if kind == "system" and d.get("subtype") == "compact_boundary":
            meta = d.get("compactMetadata") or {}
            if d.get("timestamp", "") >= since:
                ledger.compactions.append((session, meta.get("preTokens", 0), meta.get("postTokens", 0), model))
            items, pending, prev_prefix = [], [], 0
        elif kind == "attachment":
            item = attachment_item(d.get("attachment") or {})
            if item:
                pending.append(item)
        elif kind == "user":
            new = user_items(d, tool_names)
            pending.extend(new)
            in_window = d.get("timestamp", "") >= since
            if (d.get("origin") or {}).get("kind") == "human" and in_window:
                ledger.sessions[session]["human prompts"] += 1
            for block in d["message"]["content"] if isinstance(d["message"]["content"], list) and in_window else []:
                if block.get("type") == "tool_result" and block.get("is_error"):
                    ledger.tool_errors[tool_names.get(block.get("tool_use_id"), "?")] += 1
            if d.get("isCompactSummary") and ledger.compactions and ledger.compactions[-1][0] == session and d.get("timestamp", "") >= since:
                s, pre, post, m = ledger.compactions[-1]
                p = price(m or "opus-5-5")
                est = pre * p[2] / 1e6 + text_len(d["message"]["content"]) / CHARS_PER_TOKEN * p[1] / 1e6
                ledger.cost[("compaction call (estimated)", "cache read + output")] += est
                ledger.by_who[(who, "compaction (est.)")] += est
                ledger.sessions[session]["cost"] += est
        elif kind == "assistant":
            msg = d.get("message") or {}
            for block in msg.get("content") or []:
                if block.get("type") == "tool_use":
                    tool_names[block["id"]] = block["name"]
                    if d.get("timestamp", "") >= since:
                        ledger.tool_calls[block["name"]] += 1
                        ledger.tool_sessions[block["name"]].add(session)
            rid = d.get("requestId") or msg.get("id")
            usage, model_now = msg.get("usage"), msg.get("model", "")
            p = price(model_now)
            if not rid or rid in seen or not usage or not p:
                continue
            seen.add(rid)
            model = model_now
            prefix = usage["input_tokens"] + usage["cache_creation_input_tokens"] + usage["cache_read_input_tokens"]
            first = not items
            if first:
                est = [(s, c / CHARS_PER_TOKEN) for s, c in pending]
                shrink = min(1.0, 0.9 * prefix / max(sum(t for _, t in est), 1))
                est = [(s, t * shrink) for s, t in est]
                items = [["static: system prompt + tool schemas", prefix - sum(t for _, t in est)]]
                items += [[s, t] for s, t in est]
            else:
                delta = max(prefix - prev_prefix - prev_out, 0)
                chars = sum(c for _, c in pending)
                items += [[s, delta * c / chars] for s, c in pending] if chars else [["harness reminders", delta]]
            pending = []
            ts = d.get("timestamp", "")
            out, think = final[rid]
            if ts >= since:
                dollars = charge(ledger, items, usage, p, who)
                w1h = (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
                ledger.billed += (usage["input_tokens"] * p[0] + out * p[1] + usage["cache_read_input_tokens"] * p[2]
                                  + (usage["cache_creation_input_tokens"] - w1h) * p[3] + w1h * p[4]) / 1e6
                for source, tok in (("output: thinking", think), ("output: text + tool calls", out - think)):
                    ledger.cost[(source, "output")] += tok * p[1] / 1e6
                    ledger.tokens[(source, "output")] += tok
                ledger.by_who[(who, "output")] += out * p[1] / 1e6
                ledger.by_model[model_now] += dollars + out * p[1] / 1e6
                ledger.sessions[session]["cost"] += dollars + out * p[1] / 1e6
                ledger.sessions[session]["requests"] += 1
                ledger.sessions[session]["cache read"] += usage["cache_read_input_tokens"]
                ledger.sessions[session]["prefix"] += prefix
                if first and who == "main" and len(seen) == 1:
                    ledger.first_prefix.append(prefix)
                elif not first and usage["cache_creation_input_tokens"] > 0.5 * prefix:
                    ledger.cold.append((session, prev_ts, ts, usage["cache_creation_input_tokens"], model_now))
            items += [["history: thinking", think], ["history: text + tool calls", out - think]]
            prev_prefix, prev_out, prev_ts = prefix, out, d.get("timestamp", "")


def run(since: str) -> Ledger:
    ledger = Ledger()
    for main in sorted(PROJECTS.glob("*/*.jsonl")):
        session = main.stem
        walk(main, ledger, since, session, "main")
        for sub in sorted((main.parent / session / "subagents").glob("*.jsonl")):
            meta_path = sub.with_suffix(".meta.json")
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            walk(sub, ledger, since, session, f"subagent: {meta.get('agentType', '?')}")
    return ledger


def report(ledger: Ledger) -> dict:
    total = sum(ledger.cost.values())
    by_billing, by_source = Counter(), Counter()
    for (source, billing), dollars in ledger.cost.items():
        by_billing[billing] += dollars
        group = "tool results" if source.startswith("tool: ") else source
        by_source[group] += dollars
    sessions = {s: c for s, c in ledger.sessions.items() if c["requests"]}
    prompts = sum(c["human prompts"] for c in sessions.values())
    reads = sum(t for (s, b), t in ledger.tokens.items() if b == "cache read")
    fed = sum(t for (s, b), t in ledger.tokens.items() if b != "output")
    tools = {
        name: {
            "calls": n,
            "errors": ledger.tool_errors[name],
            "session share": len(ledger.tool_sessions[name]) / max(len(sessions), 1),
            "result cost": ledger.cost[(f"tool: {name}", "cache read")]
            + ledger.cost[(f"tool: {name}", "cache write")]
            + ledger.cost[(f"tool: {name}", "uncached input")],
        }
        for name, n in ledger.tool_calls.most_common()
    }
    return {
        "total $": total,
        "sessions": len(sessions),
        "human prompts": prompts,
        "requests": sum(c["requests"] for c in sessions.values()),
        "$ per human prompt": total / max(prompts, 1),
        "requests per human prompt": sum(c["requests"] for c in sessions.values()) / max(prompts, 1),
        "cache hit rate": reads / max(fed, 1),
        "median static prefix tokens": statistics.median(ledger.first_prefix) if ledger.first_prefix else 0,
        "cold misses": len(ledger.cold),
        "cold miss write tokens": sum(c[3] for c in ledger.cold),
        "compactions": len(ledger.compactions),
        "by billing": dict(by_billing.most_common()),
        "by source": dict(by_source.most_common()),
        "by source x billing": {f"{s} | {b}": v for (s, b), v in ledger.cost.most_common()},
        "by who x billing": {f"{w} | {b}": v for (w, b), v in ledger.by_who.most_common()},
        "by model": dict(ledger.by_model.most_common()),
        "tools": tools,
        "top sessions": sorted(
            ({"session": s, **c} for s, c in sessions.items()), key=lambda r: -r["cost"]
        )[:15],
        "cold miss sample": ledger.cold[:40],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="")
    parser.add_argument("--json")
    args = parser.parse_args()
    ledger = run(args.since)
    split = sum(v for (s, b), v in ledger.cost.items() if not s.startswith("compaction call"))
    assert abs(split - ledger.billed) <= 0.001 * max(ledger.billed, 1), f"split ${split:.2f} != billed ${ledger.billed:.2f}"
    out = report(ledger)
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    total = out["total $"]
    print(f"total ${total:,.0f}  sessions {out['sessions']}  prompts {out['human prompts']}  "
          f"requests {out['requests']}  $/prompt {out['$ per human prompt']:.2f}  "
          f"hit rate {out['cache hit rate']:.1%}  static prefix {out['median static prefix tokens']:,.0f}")
    for title in ("by billing", "by source"):
        print(f"\n{title}")
        for key, dollars in out[title].items():
            print(f"  {key:<42} ${dollars:>10,.0f}  {dollars / total:6.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
