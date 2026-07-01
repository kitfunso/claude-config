#!/usr/bin/env python3
"""quiz-me: forcing-function learning gate.

Append-only JSONL store at $QUIZ_HOME (default ~/.claude/quiz-me).
- deck.jsonl: cards (MC + explain-back), one per line
- results.jsonl: every attempt with timestamp + score

Gate criteria (defaults, override with env):
- QUIZ_GATE_WINDOW_DAYS (default 14): look-back window
- QUIZ_GATE_MIN_PASS    (default 0.8): pass = score >= this
- QUIZ_GATE_REQUIRE_RECENT (default 1): at least 1 attempt in last 7d if any
  cards added in last 14d
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path(os.environ.get("QUIZ_HOME", Path.home() / ".claude" / "quiz-me"))
DECK = HOME / "deck.jsonl"
RESULTS = HOME / "results.jsonl"

# spaced-rep intervals in days; index advances on correct, resets on wrong
INTERVALS = [1, 3, 7, 14, 30, 60, 120]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_files() -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    DECK.touch(exist_ok=True)
    RESULTS.touch(exist_ok=True)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def append_jsonl(path: Path, row: dict) -> None:
    ensure_files()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def card_id() -> str:
    return uuid.uuid4().hex[:12]


# ----- card creation -----

def cmd_add_mc(args: argparse.Namespace) -> int:
    cid = args.id or card_id()
    options = [o.strip() for o in args.options.split("|") if o.strip()]
    if len(options) < 2:
        print("error: need >=2 options separated by |", file=sys.stderr)
        return 2
    if not 0 <= args.answer < len(options):
        print(f"error: answer index {args.answer} out of range 0..{len(options)-1}", file=sys.stderr)
        return 2
    row = {
        "id": cid,
        "type": "mc",
        "feature": args.feature,
        "concept": args.concept,
        "question": args.question,
        "options": options,
        "answer_idx": args.answer,
        "explanation": args.explanation or "",
        "source_ref": args.source_ref or "",
        "created_at": now_iso(),
    }
    append_jsonl(DECK, row)
    print(cid)
    return 0


def cmd_add_explain(args: argparse.Namespace) -> int:
    cid = args.id or card_id()
    row = {
        "id": cid,
        "type": "explain",
        "feature": args.feature,
        "concept": args.concept,
        "prompt": args.prompt,
        "rubric": args.rubric,
        "source_ref": args.source_ref or "",
        "created_at": now_iso(),
    }
    append_jsonl(DECK, row)
    print(cid)
    return 0


# ----- attempts -----

def cmd_record(args: argparse.Namespace) -> int:
    if not 0.0 <= args.score <= 1.0:
        print("error: score must be 0.0..1.0", file=sys.stderr)
        return 2
    row = {
        "id": uuid.uuid4().hex[:12],
        "card_id": args.card_id,
        "score": args.score,
        "feature": args.feature or "",
        "notes": args.notes or "",
        "ts": now_iso(),
    }
    append_jsonl(RESULTS, row)
    print(row["id"])
    return 0


# ----- scheduling -----

def _last_result_per_card(results: list[dict]) -> dict[str, list[dict]]:
    by_card: dict[str, list[dict]] = {}
    for r in results:
        by_card.setdefault(r["card_id"], []).append(r)
    for cid in by_card:
        by_card[cid].sort(key=lambda x: x["ts"])
    return by_card


def _interval_for_card(history: list[dict], min_pass: float) -> int:
    """Return days until next due based on streak of correct attempts."""
    streak = 0
    for r in history:
        if r["score"] >= min_pass:
            streak += 1
        else:
            streak = 0
    if streak == 0:
        return 0  # due immediately on next pass attempt? No — see _due_at
    idx = min(streak - 1, len(INTERVALS) - 1)
    return INTERVALS[idx]


def _due_at(card: dict, history: list[dict], min_pass: float) -> datetime:
    """When is this card next due?"""
    created = datetime.fromisoformat(card["created_at"])
    if not history:
        return created  # due now
    last = history[-1]
    last_ts = datetime.fromisoformat(last["ts"])
    if last["score"] < min_pass:
        return last_ts  # due immediately (failed)
    days = _interval_for_card(history, min_pass)
    return last_ts + timedelta(days=days)


def cmd_due(args: argparse.Namespace) -> int:
    cards = read_jsonl(DECK)
    results = read_jsonl(RESULTS)
    by_card = _last_result_per_card(results)
    min_pass = float(os.environ.get("QUIZ_GATE_MIN_PASS", "0.8"))
    now = datetime.now(timezone.utc)

    due = []
    for c in cards:
        hist = by_card.get(c["id"], [])
        when = _due_at(c, hist, min_pass)
        if when <= now:
            due.append((when, c))
    due.sort(key=lambda x: x[0])

    if args.feature:
        due = [(w, c) for w, c in due if c.get("feature") == args.feature]

    limit = args.count or 5
    selected = [c for _, c in due[:limit]]

    if args.json:
        print(json.dumps(selected, ensure_ascii=False, indent=2))
    else:
        if not selected:
            print("no cards due")
            return 0
        for c in selected:
            tag = "[MC]" if c["type"] == "mc" else "[EXP]"
            print(f"{tag} {c['id']} {c.get('feature','')} :: {c.get('concept','')}")
    return 0


# ----- gate -----

def cmd_gate(args: argparse.Namespace) -> int:
    cards = read_jsonl(DECK)
    results = read_jsonl(RESULTS)
    by_card = _last_result_per_card(results)
    min_pass = float(os.environ.get("QUIZ_GATE_MIN_PASS", "0.8"))
    window_days = int(os.environ.get("QUIZ_GATE_WINDOW_DAYS", "14"))
    require_recent = bool(int(os.environ.get("QUIZ_GATE_REQUIRE_RECENT", "1")))

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)
    recent_start = now - timedelta(days=7)

    reasons = []

    # rule 1: any card whose latest attempt failed in window -> block
    failed_recently = []
    for c in cards:
        hist = by_card.get(c["id"], [])
        if not hist:
            continue
        last = hist[-1]
        last_ts = datetime.fromisoformat(last["ts"])
        if last_ts >= window_start and last["score"] < min_pass:
            failed_recently.append((c, last["score"]))
    if failed_recently:
        reasons.append(
            f"{len(failed_recently)} card(s) failed in last {window_days}d (must re-pass): "
            + ", ".join(f"{c['id']}({s:.0%})" for c, s in failed_recently[:5])
        )

    # rule 2: cards added in last 14d must have been attempted in last 7d
    if require_recent:
        unattempted_new = []
        for c in cards:
            created = datetime.fromisoformat(c["created_at"])
            if created < window_start:
                continue
            hist = by_card.get(c["id"], [])
            attempted_recently = any(
                datetime.fromisoformat(r["ts"]) >= recent_start for r in hist
            )
            if not attempted_recently:
                unattempted_new.append(c)
        if unattempted_new:
            reasons.append(
                f"{len(unattempted_new)} new card(s) (last {window_days}d) not attempted in last 7d: "
                + ", ".join(f"{c['id']}({c.get('feature','?')})" for c in unattempted_new[:5])
            )

    # rule 3: any card whose latest attempt is overdue and failed
    overdue_failed = []
    for c in cards:
        hist = by_card.get(c["id"], [])
        if not hist:
            continue
        if hist[-1]["score"] < min_pass:
            overdue_failed.append(c)
    if overdue_failed and not failed_recently:
        # subset already in rule 1; only report if not covered
        pass

    if reasons:
        result = {"gate": "BLOCKED", "reasons": reasons}
        print(json.dumps(result, indent=2) if args.json else
              "GATE: BLOCKED\n" + "\n".join(f"  - {r}" for r in reasons))
        return 1

    result = {"gate": "PASS", "cards_total": len(cards), "attempts_total": len(results)}
    print(json.dumps(result, indent=2) if args.json else
          f"GATE: PASS ({len(cards)} cards, {len(results)} attempts)")
    return 0


# ----- stats -----

def cmd_stats(args: argparse.Namespace) -> int:
    cards = read_jsonl(DECK)
    results = read_jsonl(RESULTS)
    by_card = _last_result_per_card(results)
    min_pass = float(os.environ.get("QUIZ_GATE_MIN_PASS", "0.8"))

    by_feature: dict[str, dict] = {}
    for c in cards:
        f = c.get("feature", "unknown")
        d = by_feature.setdefault(f, {"cards": 0, "attempts": 0, "passes": 0})
        d["cards"] += 1
        for r in by_card.get(c["id"], []):
            d["attempts"] += 1
            if r["score"] >= min_pass:
                d["passes"] += 1

    pass_rate = (sum(d["passes"] for d in by_feature.values()) /
                 sum(d["attempts"] for d in by_feature.values()) if results else 0.0)

    if args.json:
        out = {
            "cards_total": len(cards),
            "attempts_total": len(results),
            "pass_rate": round(pass_rate, 3),
            "by_feature": by_feature,
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"cards:    {len(cards)}")
        print(f"attempts: {len(results)}")
        print(f"pass:     {pass_rate:.1%}")
        if by_feature:
            print("by feature:")
            for f, d in sorted(by_feature.items()):
                pr = d["passes"] / d["attempts"] if d["attempts"] else 0.0
                print(f"  {f:<30s} cards={d['cards']} attempts={d['attempts']} pass={pr:.0%}")
    return 0


# ----- get card by id -----

def cmd_get(args: argparse.Namespace) -> int:
    cards = read_jsonl(DECK)
    for c in cards:
        if c["id"] == args.id:
            print(json.dumps(c, ensure_ascii=False, indent=2))
            return 0
    print(f"not found: {args.id}", file=sys.stderr)
    return 2


# ----- main -----

def main() -> int:
    ensure_files()
    p = argparse.ArgumentParser(prog="quiz", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add-mc", help="add a multiple-choice card")
    a.add_argument("--feature", required=True, help="feature/PR identifier")
    a.add_argument("--concept", required=True, help="short concept label")
    a.add_argument("--question", required=True)
    a.add_argument("--options", required=True, help="options separated by |")
    a.add_argument("--answer", type=int, required=True, help="0-indexed correct option")
    a.add_argument("--explanation", default="")
    a.add_argument("--source-ref", default="", help="file:line or commit ref")
    a.add_argument("--id", default="")
    a.set_defaults(func=cmd_add_mc)

    a = sub.add_parser("add-explain", help="add an explain-back card")
    a.add_argument("--feature", required=True)
    a.add_argument("--concept", required=True)
    a.add_argument("--prompt", required=True, help="what the user must explain")
    a.add_argument("--rubric", required=True, help="what a passing answer must mention")
    a.add_argument("--source-ref", default="")
    a.add_argument("--id", default="")
    a.set_defaults(func=cmd_add_explain)

    a = sub.add_parser("record", help="record an attempt result")
    a.add_argument("--card-id", required=True)
    a.add_argument("--score", type=float, required=True, help="0.0 to 1.0")
    a.add_argument("--feature", default="")
    a.add_argument("--notes", default="")
    a.set_defaults(func=cmd_record)

    a = sub.add_parser("due", help="list cards due for review")
    a.add_argument("--count", type=int, default=5)
    a.add_argument("--feature", default="")
    a.add_argument("--json", action="store_true")
    a.set_defaults(func=cmd_due)

    a = sub.add_parser("gate", help="check gate; exit 0 pass, 1 blocked")
    a.add_argument("--json", action="store_true")
    a.set_defaults(func=cmd_gate)

    a = sub.add_parser("stats", help="summary stats")
    a.add_argument("--json", action="store_true")
    a.set_defaults(func=cmd_stats)

    a = sub.add_parser("get", help="print a card by id")
    a.add_argument("id")
    a.set_defaults(func=cmd_get)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
