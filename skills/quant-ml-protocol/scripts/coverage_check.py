"""Check a quant-ml-protocol plan page's coverage, reviews and challenger log before a freeze.

Usage: python coverage_check.py PLAN.html --stage {4,8,10}. Exit 0 when every
row due by that stage is closed with an accepted state, 1 otherwise.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

COLUMNS = ("item", "kind", "by", "state", "evidence", "reason")
CODES = ("no-data", "declined", "validity", "compute", "row-floor")
REFUSED = re.compile(
    r"under-?powered|small sample|sample size|multiplicit|expect\w* (to be )?null|"
    r"likely null|empty shortlist|no time|time budget|low power|would not survive|not worth",
    re.IGNORECASE,
)
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
DIGIT = re.compile(r"\d")
# Dates and file names carry digits that are not results, so they never count as a value.
NOT_A_VALUE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|(?=\S*[A-Za-z])\S*[\\/]\S*|\S+\.(?:html?|jsonl?|csv|py|md|parquet|txt|ipynb)\b",
    re.IGNORECASE,
)
RUNG_KINDS = ("mechanism", "family", "gauntlet")
REQUIRED_KINDS = {
    4: ("driver", "data-route", "tier", "target", "horizon"),
    8: RUNG_KINDS,
}
REQUIRED_IDS = {
    8: tuple(f"M{i}" for i in range(1, 11))
    + tuple(f"F{i}" for i in range(1, 7))
    + tuple(f"G{i}" for i in range(1, 5)),
}
CHALLENGER_COLUMNS = {
    "round": "round",
    "declared": "declared",
    "change": "the one change",
    "interval": "paired interval",
    "verdict": "verdict",
}
REVIEW_COLUMNS = {
    "gate": "gate",
    "reviewer": "reviewer",
    "date": "date",
    "page": "page",
    "findings": "findings",
    "rejected": "rejected",
}
REQUIRED_REVIEWS = {
    4: (("plan", "grill"), ("plan", "plan-eng-review"), ("plan", "codex"), ("stage 4", "critic"), ("stage 4", "codex")),
    8: (("stage 8", "critic"), ("stage 8", "codex")),
}
NOT_RUN = "not run:"


@dataclass(frozen=True)
class Row:
    item: str
    kind: str
    by: str
    state: str
    evidence: str
    reason: str


class _TableParser(HTMLParser):
    """Collects cell text from the table with one id, one list per row."""

    def __init__(self, table_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.table_id = table_id
        self.found = False
        self.rows: list[list[str]] = []
        self._depth = 0
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            if self._depth:
                self._depth += 1
            elif dict(attrs).get("id") == self.table_id:
                self.found, self._depth = True, 1
            return
        if self._depth != 1:
            return
        # Close implicitly ended cells and rows, which HTML allows and html.parser does not infer.
        if tag in ("td", "th", "tr"):
            self._close_cell()
        if tag == "tr":
            self._close_row()
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if not self._depth:
            return
        if tag == "table":
            if self._depth == 1:
                self._close_cell()
                self._close_row()
            self._depth -= 1
        elif self._depth == 1 and tag in ("td", "th"):
            self._close_cell()
        elif self._depth == 1 and tag == "tr":
            self._close_cell()
            self._close_row()

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def _close_cell(self) -> None:
        if self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
        self._cell = None

    def _close_row(self) -> None:
        if self._row:
            self.rows.append(self._row)
        self._row = None


def read_table(html: str, table_id: str) -> list[list[str]] | None:
    parser = _TableParser(table_id)
    parser.feed(html)
    parser.close()
    return parser.rows if parser.found else None


def read_rows(html: str) -> tuple[list[Row], list[str]]:
    table = read_table(html, "coverage")
    if table is None:
        return [], ['no <table id="coverage"> on the page']
    if not table:
        return [], ["the coverage table has no rows"]
    header = [h.strip().lower() for h in table[0]]
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        return [], [f"coverage header lacks column(s): {', '.join(missing)}"]
    at = {c: header.index(c) for c in COLUMNS}
    rows = []
    for cells in table[1:]:
        cells = cells + [""] * (len(header) - len(cells))
        rows.append(Row(*(cells[at[c]].strip() for c in COLUMNS)))
    return rows, []


def _has_value(text: str) -> bool:
    return bool(DIGIT.search(NOT_A_VALUE.sub(" ", text)))


def _stage_of(row: Row) -> int | None:
    return int(row.by) if row.by.isdigit() else None


def _due_by(row: Row, stage: int) -> bool:
    due = _stage_of(row)
    return due is not None and due <= stage


def _blocked_problem(row: Row) -> str | None:
    code, sep, detail = row.reason.partition(":")
    code = code.strip().lower()
    if not sep or code not in CODES:
        return f"blocked needs a reason code ({', '.join(c + ':' for c in CODES)}), got {row.reason!r}"
    if not detail.strip():
        return f"{code}: needs its detail"
    if code == "declined" and not DATE.search(detail):
        return "declined: needs the date of the user's answer (YYYY-MM-DD)"
    if code in ("compute", "row-floor") and not DIGIT.search(detail):
        return f"{code}: needs its number"
    if code == "row-floor" and row.kind.lower() in RUNG_KINDS:
        return "row-floor: is never a reason on a rung; a rung the sample cannot support runs as exploratory context"
    if code in ("no-data", "validity") and not row.evidence:
        return f"{code}: needs its evidence (the search log, or the page that shows the blocker)"
    return None


def _row_problem(row: Row, stage: int) -> str | None:
    due = _stage_of(row)
    state = row.state.lower()
    if due is None:
        return f"By {row.by!r} is not a stage number"
    if due > stage:
        return None if state in ("pending", "ran", "blocked", "") else f"unknown state {row.state!r}"
    if state == "ran":
        return None if _has_value(row.evidence) else "ran needs evidence with its metric value (a dated file name is not one)"
    if state == "blocked":
        if REFUSED.search(row.reason):
            return f"refused reason: {row.reason!r}"
        return _blocked_problem(row)
    return f"open (state {row.state or 'empty'!r}) but due by stage {due}"


def _keyed_rows(table: list[list[str]], columns: dict[str, str], name: str) -> tuple[list[dict[str, str]], str | None]:
    header = [h.strip().lower() for h in table[0]]
    at = {}
    for key, prefix in columns.items():
        hits = [i for i, h in enumerate(header) if h.startswith(prefix)]
        if not hits:
            return [], f"{name} header lacks a column starting {prefix!r}"
        at[key] = hits[0]
    padded = (cells + [""] * (len(header) - len(cells)) for cells in table[1:])
    return [{k: cells[i].strip() for k, i in at.items()} for cells in padded], None


def _review_problems(row: dict[str, str], reviewer: str) -> list[str]:
    problems = [] if DATE.search(row["date"]) else ["needs its date (YYYY-MM-DD)"]
    if row["findings"].lower().startswith(NOT_RUN):
        if reviewer != "codex":
            return problems + ["only codex may be not run: the grill, plan-eng-review and the critic always run"]
        return problems + ([] if row["findings"][len(NOT_RUN):].strip() else ["not run: needs its reason"])
    if not row["page"]:
        problems.append("needs the page its findings are on")
    if not DIGIT.search(row["findings"]):
        problems.append("needs its findings count")
    if not DIGIT.search(row["rejected"]):
        problems.append("needs its rejected count, with a reason for each")
    return problems


def check_reviews(html: str, stage: int) -> list[str]:
    table = read_table(html, "reviews")
    if table is None:
        return ['no <table id="reviews"> on the page: the plan review is due before stage 1 part one freezes']
    rows, problem = _keyed_rows(table, REVIEW_COLUMNS, "reviews") if table else ([], "the reviews table has no rows")
    if problem:
        return [problem]
    problems = []
    for due, needed in REQUIRED_REVIEWS.items():
        if due > stage:
            continue
        for gate, reviewer in needed:
            hits = [r for r in rows if " ".join(r["gate"].lower().split()) == gate and reviewer in r["reviewer"].lower()]
            if not hits:
                problems.append(f"no {reviewer} review at the {gate} gate")
                continue
            problems.extend(f"{reviewer} at the {gate} gate: {p}" for p in _review_problems(hits[-1], reviewer))
    return problems


def check_challengers(html: str) -> list[str]:
    table = read_table(html, "challengers")
    if table is None:
        return ['no <table id="challengers"> on the page: the challenger log is due by stage 8']
    if len(table) < 2:
        return ["the challenger log has no rounds"]
    rows, problem = _keyed_rows(table, CHALLENGER_COLUMNS, "challenger log")
    if problem:
        return [problem]
    problems = []
    for get in rows:
        name = f"challenger round {get['round'] or '(no id)'}"
        if not DATE.search(get["declared"]):
            problems.append(f"{name}: needs the date it was declared (YYYY-MM-DD)")
        if not get["change"]:
            problems.append(f"{name}: needs its one change")
        if not _has_value(get["interval"]):
            problems.append(f"{name}: needs its paired interval")
        if not get["verdict"]:
            problems.append(f"{name}: needs its verdict")
    return problems


def check(html: str, stage: int) -> tuple[list[str], dict[str, int]]:
    rows, problems = read_rows(html)
    if problems:
        return problems, {}
    for row in rows:
        problem = _row_problem(row, stage)
        if problem:
            problems.append(f"{row.item or '(no item)'}: {problem}")
    for due, kinds in REQUIRED_KINDS.items():
        if due > stage:
            continue
        for kind in kinds:
            if not any(r.kind.lower() == kind and _due_by(r, due) for r in rows):
                problems.append(f"no {kind} row due by stage {due}")
    for due, ids in REQUIRED_IDS.items():
        if due > stage:
            continue
        for rung in ids:
            if not any(re.match(rf"{rung}\b", r.item) and _due_by(r, due) for r in rows):
                problems.append(f"no {rung} row due by stage {due}: every rung is a row (references/model-families.md)")
    problems.extend(check_reviews(html, stage))
    if stage >= 8:
        problems.extend(check_challengers(html))
    counts = {s: sum(r.state.lower() == s for r in rows) for s in ("ran", "blocked")}
    counts["pending"] = len(rows) - counts["ran"] - counts["blocked"]
    return problems, counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan", type=Path)
    ap.add_argument("--stage", type=int, choices=(4, 8, 10), required=True)
    args = ap.parse_args(argv)
    problems, counts = check(args.plan.read_text(encoding="utf-8"), args.stage)
    if problems:
        print(f"coverage fails at stage {args.stage}: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(
        f"coverage passes at stage {args.stage}: "
        f"{counts['ran']} ran, {counts['blocked']} blocked, {counts['pending']} pending"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
