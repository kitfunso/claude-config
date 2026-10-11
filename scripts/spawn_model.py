"""Was the model of each sub-agent named in the Agent call, or did it fall to the type's default?"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.argv = [sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else "14"]
from subagent_roles import CRITIC, read  # noqa: E402
from token_burn import CUTOFF, ROOT, weight  # noqa: E402


def spawn_index(paths: list[Path]) -> dict[str, dict]:
    """Agent tool_use inputs keyed by tool_use id."""
    index: dict[str, dict] = {}
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"name":"Agent"' not in line and '"name": "Agent"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for b in (rec.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Agent":
                        index[b.get("id", "")] = b.get("input") or {}
    return index


def main() -> None:
    paths = [p for p in ROOT.rglob("*.jsonl") if p.stat().st_mtime >= CUTOFF.timestamp()]
    index = spawn_index(paths)
    total = 0.0
    cell: dict[tuple[str, str, str], float] = defaultdict(float)
    cell_n: Counter[tuple[str, str, str]] = Counter()
    kind_cell: dict[tuple[str, str], float] = defaultdict(float)
    kind_n: Counter[tuple[str, str]] = Counter()
    unmatched = 0
    for path in paths:
        calls = read(path)
        if not calls:
            continue
        w = sum(weight(c) for c in calls)
        total += w
        if "subagents" not in path.parts:
            continue
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        kind, desc = meta.get("agentType", "?"), meta.get("description", "")
        inp = index.get(meta.get("toolUseId", ""))
        if inp is None:
            unmatched += 1
            named = "spawn call not found"
        else:
            named = f"named {inp['model']}" if inp.get("model") else "not named"
        spawns = sum(1 for c in calls for t in c["tools"] if t[0] == "Agent")
        if spawns >= 2:
            role = "orchestrator"
        elif kind == "senior-code-reviewer" or CRITIC.search(desc):
            role = "critic"
        else:
            role = "leaf"
        ran = calls[0]["model"]
        cell[(role, ran, named)] += w
        cell_n[(role, ran, named)] += 1
        if ran == "opus" and role == "leaf":
            kind_cell[(kind, named)] += w
            kind_n[(kind, named)] += 1

    print(f"## role | ran on | model in the Agent call: share of ALL burn (agents). {len(index):,} Agent calls indexed, {unmatched} sub-agents unmatched")
    for key, w in sorted(cell.items(), key=lambda kv: -kv[1])[:18]:
        print(f"  {w / total * 100:5.1f}%  {cell_n[key]:4d}  {' | '.join(key)}")
    print("\n## Opus leaf workers by type and how the model was chosen")
    for key, w in sorted(kind_cell.items(), key=lambda kv: -kv[1])[:14]:
        print(f"  {w / total * 100:5.1f}%  {kind_n[key]:4d}  {' | '.join(key)}")


if __name__ == "__main__":
    main()
