"""Seeded recipe roller for frontend-mix. Rolls N distinct tech mixes per round,
enforces clash/perf/novelty rules, writes manifest.json, board.html, and history.json."""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CATALOG = SKILL_DIR / "catalog.json"
HISTORY = SKILL_DIR / "history.json"
MAX_TRIES = 5000


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_kv(items: list[str] | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for item in items or []:
        slot, _, value = item.partition("=")
        out.setdefault(slot, []).append(value)
    return out


HEX = r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b"


def _field(text: str, label: str) -> str | None:
    m = re.search(r"\*\*" + re.escape(label) + r":\*\*\s*([^\n]*)", text)
    return m.group(1).strip() if m else None


def _font(text: str, label: str) -> str | None:
    raw = _field(text, label)
    if not raw:
        return None
    name = re.split(r"\s+[—–-]\s+|\(|,|·", raw)[0].strip().strip("*` ")
    return name or None


def load_design(path: Path) -> dict:
    """Lock palette + type from a DESIGN.md written in the /design-consultation shape."""
    text = path.read_text(encoding="utf-8")
    display, body, data = _font(text, "Display/Hero"), _font(text, "Body"), _font(text, "Data/Tables")
    primary = _field(text, "Primary") or _field(text, "Accent") or ""
    secondary = _field(text, "Secondary") or ""
    neutrals = re.findall(HEX, _field(text, "Neutrals") or "")
    accent = (re.findall(HEX, primary) or [None])[0]
    muted = (re.findall(HEX, secondary) or [None])[0]
    missing = [k for k, v in {"Display/Hero": display, "Body": body, "Primary hex": accent, "Neutrals hex": neutrals}.items() if not v]
    if missing:
        sys.exit(f"{path}: cannot lock taste, DESIGN.md lacks {missing}; keep the bold labels from references/design-standards.md")
    fonts = [f"{display}:wght@400;600;700", f"{body}:wght@400;500"]
    if data and data not in (display, body):
        fonts.append(f"{data}:wght@400;500")
    tokens = {"bg": neutrals[0], "ink": neutrals[-1], "accent": accent, "muted": muted or neutrals[len(neutrals) // 2]}
    dark = (_field(text, "Direction") or "").lower()
    return {"source": str(path), "fonts": fonts, "tokens": tokens,
            "single_world": any(w in dark for w in ("dark", "terminal", "cinematic", "neon"))}


def inject_design(cat: dict, design: dict) -> dict[str, list[str]]:
    cat["slots"]["palette"]["design-md"] = {"label": f"DESIGN.md palette ({design['source']})", "tokens": design["tokens"],
                                            "single_world": design["single_world"]}
    cat["slots"]["type"]["design-md"] = {"label": f"DESIGN.md type ({design['source']})", "fonts": design["fonts"]}
    return {"palette": ["design-md"], "type": ["design-md"]}


def violates(recipe: dict, slots: dict, max_heavy: int) -> str | None:
    heavy = 0
    for slot, opt in recipe.items():
        spec = slots[slot][opt]
        heavy += "heavy" in spec.get("tags", [])
        for other_slot, banned in spec.get("conflicts", {}).items():
            if recipe.get(other_slot) in banned:
                return f"{slot}={opt} clashes with {other_slot}={recipe[other_slot]}"
        for other_slot, allowed in spec.get("requires", {}).items():
            if other_slot in recipe and recipe[other_slot] not in allowed:
                return f"{slot}={opt} needs {other_slot} in {allowed}"
    if heavy > max_heavy:
        return f"{heavy} GPU-heavy layers (max {max_heavy})"
    return None


def triple(recipe: dict) -> tuple:
    return (recipe.get("hero"), recipe.get("material"), recipe.get("motion") or recipe.get("runtime"))


def roll_round(cat: dict, mode: str, n: int, rng: random.Random, locks: dict, avoid: dict, history: list) -> list[dict]:
    slot_names = cat["modes"][mode]
    slots = cat["slots"]
    max_heavy = cat.get("max_heavy_per_variant", 2)
    seen_triples = {tuple(h["triple"]) for h in history}
    seen_pairs = {(h["triple"][0], h["triple"][1]) for h in history}
    chosen: list[dict] = []
    tries = 0
    while len(chosen) < n and tries < MAX_TRIES:
        tries += 1
        recipe = {}
        for slot in slot_names:
            if slot in locks:
                recipe[slot] = rng.choice(locks[slot])
                continue
            pool = [o for o in slots[slot] if o not in avoid.get(slot, [])]
            recipe[slot] = rng.choice(pool)
        if violates(recipe, slots, max_heavy):
            continue
        if triple(recipe) in seen_triples:
            continue
        free = [s for s in slot_names if s not in locks]
        max_shared = 2 if len(free) >= 5 else 1
        distinct_ok = all(
            ("hero" in locks or recipe["hero"] != c["hero"])
            and ("palette" in locks or recipe["palette"] != c["palette"])
            and sum(recipe[s] == c[s] for s in free) <= max_shared
            for c in chosen
        )
        if not distinct_ok:
            continue
        chosen.append(recipe)
    if len(chosen) < n:
        sys.exit(f"could only roll {len(chosen)}/{n} distinct recipes after {MAX_TRIES} tries; loosen --lock/--avoid")
    tech_locked = "hero" in locks or "material" in locks
    if not any((c["hero"], c["material"]) not in seen_pairs for c in chosen) and not tech_locked:
        chosen[-1] = force_novel_pair(chosen, cat, mode, rng, avoid, seen_pairs, seen_triples)
    return chosen


def force_novel_pair(chosen, cat, mode, rng, avoid, seen_pairs, seen_triples):
    slots = cat["slots"]
    for _ in range(MAX_TRIES):
        recipe = dict(chosen[-1])
        recipe["hero"] = rng.choice([o for o in slots["hero"] if o not in avoid.get("hero", [])])
        recipe["material"] = rng.choice([o for o in slots["material"] if o not in avoid.get("material", [])])
        if (recipe["hero"], recipe["material"]) in seen_pairs or triple(recipe) in seen_triples:
            continue
        if violates(recipe, slots, cat.get("max_heavy_per_variant", 2)):
            continue
        if any(recipe["hero"] == c["hero"] for c in chosen[:-1]):
            continue
        return recipe
    return chosen[-1]


def describe(recipe: dict, cat: dict) -> dict:
    slots = cat["slots"]
    cdn_keys: list[str] = []
    fonts: list[str] = []
    warnings: list[str] = []
    for slot, opt in recipe.items():
        spec = slots[slot][opt]
        cdn_keys += [k for k in spec.get("cdn", []) if k not in cdn_keys]
        fonts += spec.get("fonts", [])
        if "heavy" in spec.get("tags", []):
            warnings.append(f"{slot}={opt} is GPU-heavy: cap pixelRatio 1.5, half-res on mobile")
    imports = {}
    scripts = []
    for key in cdn_keys:
        entry = cat["cdn"][key]
        imports.update(entry.get("importmap", {}))
        scripts += [v for k, v in entry.items() if k in ("script", "scrolltrigger")]
    return {
        "recipe": recipe,
        "labels": {s: slots[s][o]["label"] for s, o in recipe.items()},
        "palette_tokens": slots["palette"][recipe["palette"]].get("tokens"),
        "single_world": slots["palette"][recipe["palette"]].get("single_world", False),
        "fonts": fonts,
        "importmap": imports,
        "scripts": scripts,
        "warnings": warnings,
    }


def write_manifest(out: Path, mode: str, seed: int, brief: str, variants: list[dict], design: dict | None) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "skill": "frontend-mix",
        "rolled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode,
        "seed": seed,
        "brief": brief,
        "design_md": design["source"] if design else None,
        "variants": [
            {"id": f"v{i + 1}", "file": f"variants/v{i + 1}-{v['recipe']['hero']}.html", **v}
            for i, v in enumerate(variants)
        ],
    }
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def print_table(variants: list[dict], slot_names: list[str]) -> None:
    print("| id | " + " | ".join(slot_names) + " |")
    print("|---|" + "---|" * len(slot_names))
    for i, v in enumerate(variants):
        print(f"| v{i + 1} | " + " | ".join(v["recipe"][s] for s in slot_names) + " |")
    for i, v in enumerate(variants):
        for w in v["warnings"]:
            print(f"  v{i + 1}: {w}")


def write_board(out: Path) -> Path:
    manifest = load_json(out / "manifest.json", None)
    if not manifest:
        sys.exit(f"no manifest.json in {out}; roll first")
    cards = []
    for v in manifest["variants"]:
        chips = "".join(f"<span>{s}: {o}</span>" for s, o in v["recipe"].items())
        cards.append(
            f'<section class="card"><header><b>{v["id"]}</b> {chips}</header>'
            f'<iframe src="{v["file"]}" loading="lazy" title="{v["id"]}"></iframe>'
            f'<textarea data-id="{v["id"]}" placeholder="notes for {v["id"]}: keep / kill / remix which slot?"></textarea></section>'
        )
    html = BOARD_TEMPLATE.replace("{{BRIEF}}", manifest["brief"]).replace("{{SEED}}", str(manifest["seed"])).replace("{{CARDS}}", "\n".join(cards))
    path = out / "board.html"
    path.write_text(html, encoding="utf-8")
    return path


def approve(out: Path, vid: str) -> None:
    manifest = load_json(out / "manifest.json", None)
    if not manifest:
        sys.exit("no manifest.json to approve from")
    match = [v for v in manifest["variants"] if v["id"] == vid]
    if not match:
        sys.exit(f"{vid} not in manifest")
    history = load_json(HISTORY, [])
    history.append({
        "approved_at": time.strftime("%Y-%m-%d"),
        "brief": manifest["brief"],
        "seed": manifest["seed"],
        "id": vid,
        "recipe": match[0]["recipe"],
        "triple": list(triple(match[0]["recipe"])),
    })
    HISTORY.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"recorded {vid} for '{manifest['brief']}' in {HISTORY}")


def record_round(mode: str, seed: int, brief: str, variants: list[dict]) -> None:
    history = load_json(HISTORY, [])
    for i, v in enumerate(variants):
        history.append({
            "rolled_at": time.strftime("%Y-%m-%d"),
            "brief": brief,
            "seed": seed,
            "id": f"v{i + 1}",
            "mode": mode,
            "recipe": v["recipe"],
            "triple": list(triple(v["recipe"])),
        })
    HISTORY.write_text(json.dumps(history, indent=2), encoding="utf-8")


BOARD_TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>frontend-mix board</title>
<style>
body{margin:0;background:#101211;color:#e8ece7;font:14px/1.5 system-ui,sans-serif}
.top{padding:16px 20px;border-bottom:1px solid #2c332d;display:flex;gap:20px;align-items:baseline}
.top b{font-size:18px}.top code{color:#9fb3a3}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:16px;padding:16px}
.card{background:#171a18;border:1px solid #2c332d;display:flex;flex-direction:column}
.card header{padding:8px 10px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;border-bottom:1px solid #2c332d}
.card header span{font:11px ui-monospace,monospace;background:#232824;padding:2px 6px;border-radius:2px;color:#b9c7bc}
iframe{width:100%;aspect-ratio:16/10;border:0;background:#fff}
textarea{width:100%;box-sizing:border-box;min-height:64px;background:#0f1110;color:#e8ece7;border:0;border-top:1px solid #2c332d;padding:8px 10px;font:13px system-ui;resize:vertical}
button{margin:0 20px 20px;background:#7cff6b;color:#0a0c0a;border:0;padding:10px 16px;font-weight:600;cursor:pointer}
pre{margin:0 20px 20px;background:#171a18;padding:12px;white-space:pre-wrap;border:1px solid #2c332d}
</style></head><body>
<div class="top"><b>frontend-mix</b><span>{{BRIEF}}</span><code>seed {{SEED}}</code></div>
<main>{{CARDS}}</main>
<button id="copy">Copy feedback as JSON</button><pre id="out"></pre>
<script>
document.getElementById('copy').onclick=()=>{const fb={};document.querySelectorAll('textarea').forEach(t=>{if(t.value.trim())fb[t.dataset.id]=t.value.trim()});
const s=JSON.stringify(fb,null,2);document.getElementById('out').textContent=s;navigator.clipboard&&navigator.clipboard.writeText(s).catch(()=>{});};
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="frontend-mix recipe roller")
    ap.add_argument("--mode", choices=["web", "video"], default="web")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--brief", default="")
    ap.add_argument("--design", type=Path, help="DESIGN.md to lock palette + type from (dice choose tech, never taste)")
    ap.add_argument("--lock", action="append", help="slot=option, repeatable")
    ap.add_argument("--avoid", action="append", help="slot=option, repeatable")
    ap.add_argument("--board", type=Path, help="write board.html for an existing round dir")
    ap.add_argument("--approve", nargs=2, metavar=("OUT", "VID"), help="record the winning variant")
    ap.add_argument("--no-history", action="store_true", help="do not append this round to history.json")
    args = ap.parse_args()

    if args.board:
        print(write_board(args.board))
        return
    if args.approve:
        approve(Path(args.approve[0]), args.approve[1])
        return
    if not args.out:
        ap.error("--out is required to roll")

    cat = load_json(CATALOG, None)
    seed = args.seed if args.seed is not None else int(time.time()) % 1_000_000
    rng = random.Random(seed)
    history = load_json(HISTORY, [])
    locks = parse_kv(args.lock)
    design = load_design(args.design) if args.design else None
    if design:
        locks = {**inject_design(cat, design), **{k: v for k, v in locks.items() if k not in ("palette", "type")}}
        print(f"taste locked from {design['source']}: {design['tokens']} / {design['fonts']}")
    else:
        print("WARNING: no --design; palette and type are dice, use only for exploration before a DESIGN.md exists")
    recipes = roll_round(cat, args.mode, args.n, rng, locks, parse_kv(args.avoid), history)
    variants = [describe(r, cat) for r in recipes]
    path = write_manifest(args.out, args.mode, seed, args.brief, variants, design)
    if not args.no_history:
        record_round(args.mode, seed, args.brief, variants)
    print(f"seed {seed} -> {path}")
    print_table(variants, cat["modes"][args.mode])


if __name__ == "__main__":
    main()
