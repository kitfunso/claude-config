"""Eyes-on QA for frontend-mix variants: headless Chromium screenshots at desktop and
mobile sizes, console-error capture, and a stitched contact sheet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SIZES = {"desktop": (1440, 900), "mobile": (390, 844)}


def shoot(variants: Path, out: Path, sheet: Path | None, wait_ms: int) -> int:
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(variants.glob("*.html"))
    if not files:
        sys.exit(f"no .html in {variants}")
    report: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for html in files:
            entry: dict = {"errors": [], "shots": {}}
            for name, (w, h) in SIZES.items():
                page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                page.on("pageerror", lambda e, entry=entry: entry["errors"].append(f"pageerror: {e}"))
                page.on("console", lambda m, entry=entry: entry["errors"].append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
                page.goto(html.resolve().as_uri(), wait_until="load")
                page.wait_for_timeout(wait_ms)
                shot = out / f"{html.stem}-{name}.png"
                page.screenshot(path=str(shot), full_page=False)
                entry["shots"][name] = str(shot)
                page.close()
            report[html.name] = entry
        browser.close()
    (out / "qa-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    bad = 0
    for name, entry in report.items():
        flag = "ERR" if entry["errors"] else "ok "
        bad += bool(entry["errors"])
        print(f"{flag} {name}")
        for err in entry["errors"][:5]:
            print(f"      {err[:200]}")
    if sheet:
        stitch(report, sheet)
        print(f"sheet -> {sheet}")
    return bad


def stitch(report: dict, sheet: Path) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed; skipping contact sheet (pip install pillow)")
        return
    cell_w, cell_h, pad = 720, 450, 24
    rows = list(report.items())
    img = Image.new("RGB", (cell_w * 2 + pad * 3, (cell_h + pad + 28) * len(rows) + pad), "#101211")
    draw = ImageDraw.Draw(img)
    y = pad
    for name, entry in rows:
        label = f"{name}   {'ERRORS: ' + str(len(entry['errors'])) if entry['errors'] else 'clean'}"
        draw.text((pad, y), label, fill="#e8ece7")
        y += 28
        x = pad
        for key in ("desktop", "mobile"):
            shot = Image.open(entry["shots"][key]).convert("RGB")
            shot.thumbnail((cell_w, cell_h))
            img.paste(shot, (x, y))
            x += cell_w + pad
        y += cell_h + pad
    sheet.parent.mkdir(parents=True, exist_ok=True)
    img.save(sheet)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("variants", type=Path, help="directory of variant .html files")
    ap.add_argument("--out", type=Path, help="screenshot dir (default: <variants>/../qa)")
    ap.add_argument("--sheet", type=Path, help="contact sheet png path")
    ap.add_argument("--wait", type=int, default=2500, help="ms to let shaders/fonts settle")
    args = ap.parse_args()
    out = args.out or args.variants.parent / "qa"
    bad = shoot(args.variants, out, args.sheet, args.wait)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
