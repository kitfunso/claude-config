"""Backtest the spawn guard on real Agent calls: what it would have moved, and what it would have let through."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.argv = [sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else "14"]
sys.path.insert(0, str(Path.home() / ".claude" / "scripts" / "hooks"))
from subagent_roles import read  # noqa: E402
from spawn_model import spawn_index  # noqa: E402
from subagent_contract import spawn_check  # noqa: E402
from token_burn import CUTOFF, ROOT, weight  # noqa: E402


def main() -> None:
    paths = [p for p in ROOT.rglob("*.jsonl") if p.stat().st_mtime >= CUTOFF.timestamp()]
    index = spawn_index(paths)
    total = 0.0
    rows: list[dict] = []
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
        inp = index.get(meta.get("toolUseId", "")) or {}
        names = Counter(t[0] for c in calls for t in c["tools"])
        rows.append({"w": w, "n": len(calls), "kind": meta.get("agentType", "?"), "desc": meta.get("description", ""),
                     "model": calls[0]["model"], "moved": spawn_check(inp) is not None,
                     "edits": names.get("Edit", 0) + names.get("Write", 0), "spawns": names.get("Agent", 0)})

    moved = [r for r in rows if r["moved"]]
    opus = [r for r in rows if r["model"] == "opus"]
    print(f"## guard would move to Sonnet {len(moved)} of {len(rows)} spawns = {sum(r['w'] for r in moved) / total * 100:.1f}% of ALL burn "
          f"(Opus sub-agents are {sum(r['w'] for r in opus) / total * 100:.1f}%)")
    print(f"   of the moved: made 5+ edits {sum(1 for r in moved if r['edits'] >= 5)} | spawned 2+ agents {sum(1 for r in moved if r['spawns'] >= 2)} "
          f"| under 5 edits {sum(1 for r in moved if r['edits'] < 5)}")
    print("\n## moved, top 40 by burn: share | calls | edits | spawns | type | description")
    for r in sorted(moved, key=lambda r: -r["w"])[:40]:
        print(f"  {r['w'] / total * 100:4.2f}%  {r['n']:4d}  {r['edits']:3d}  {r['spawns']:2d}  {r['kind'][:16]:16s} {r['desc'][:70]}")
    print("\n## moved with under 5 edits (possible false positives)")
    for r in sorted((r for r in moved if r["edits"] < 5), key=lambda r: -r["w"])[:15]:
        print(f"  {r['w'] / total * 100:4.2f}%  {r['n']:4d}  {r['edits']:3d}  {r['kind'][:16]:16s} {r['desc'][:70]}")
    passed = [r for r in opus if not r["moved"] and r["edits"] >= 5 and r["kind"] not in ("senior-code-reviewer",)]
    print(f"\n## Opus builders the guard lets through: {sum(r['w'] for r in passed) / total * 100:.1f}% of ALL burn, top 25")
    for r in sorted(passed, key=lambda r: -r["w"])[:25]:
        print(f"  {r['w'] / total * 100:4.2f}%  {r['n']:4d}  {r['edits']:3d}  {r['spawns']:2d}  {r['kind'][:16]:16s} {r['desc'][:70]}")


if __name__ == "__main__":
    main()
