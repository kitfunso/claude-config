from __future__ import annotations

from pathlib import Path

import coverage_check as cc

HEADER = "<tr><th>Item</th><th>Kind</th><th>By</th><th>State</th><th>Evidence</th><th>Reason</th></tr>"
STAGE4 = [
    ("EIA storage", "driver", "4", "ran", "docs/data-audit-2026-09-30.html, 1,004 weeks", ""),
    ("Longer history", "data-route", "4", "ran", "LSEG back to 1994, 1,660 weeks", ""),
    ("Pooled panel", "data-route", "4", "blocked", "docs/data-audit-2026-09-30.html search log",
     "no-data: searched crude-db and EIA for sibling weekly series, 3 queries, none"),
    ("Tier 1, domain", "tier", "4", "ran", "docs/feature-universe-2026-10-01.html, 12 cells", ""),
    ("Tier 2, full enumeration", "tier", "4", "ran", "docs/feature-universe-2026-10-01.html, 4,812 cells", ""),
    ("Change", "target", "4", "ran", "docs/measure-2026-09-30.html, no-change MAE 0.041", ""),
    ("1 week", "horizon", "4", "ran", "docs/measure-2026-09-30.html, n_rank 313", ""),
]
STAGE8 = (
    [(f"M{i} rung", "mechanism", "8", "ran", f"docs/grid-2026-10-02.html, rank IC +0.0{i}", "") for i in range(1, 11)]
    + [(f"F{i} family", "family", "8", "ran", f"docs/grid-2026-10-02.html, rank IC +0.0{i}", "") for i in range(1, 7)]
    + [(f"G{i} check", "gauntlet", "8", "ran", f"docs/gauntlet-2026-10-02.html, sign held in {i} of 9 years", "")
       for i in range(1, 5)]
)
CHALLENGER_HEADER = (
    "<tr><th>Round</th><th>Declared</th><th>The one change</th><th>Why (the error it aims at)</th>"
    "<th>Paired interval against the standing cell</th><th>Verdict</th><th>What it taught</th></tr>"
)
ROUNDS = [
    ("1", "2026-10-01", "the declared ladder and grid", "baseline round", "+0.02 [-0.01, +0.05]", "tie", "flat surface"),
    ("2", "2026-10-02", "excess over carry target", "always-short scored well", "+0.04 [+0.01, +0.07]", "stands", "drift"),
]
REVIEW_HEADER = (
    "<tr><th>Gate</th><th>Reviewer</th><th>Date</th><th>Page</th><th>Findings</th>"
    "<th>Rejected, with reasons</th></tr>"
)
REVIEWS = [
    ("plan", "/plan-eng-review", "2026-09-30", "docs/plan-review-2026-09-30.html", "9", "1: cadence grid kept, see page"),
    ("plan", "/codex consult", "2026-09-30", "docs/plan-review-2026-09-30.html", "6", "0"),
    ("stage 4", "critic", "2026-10-01", "docs/critic-2026-10-01.html", "4", "0"),
    ("stage 4", "/codex consult", "2026-10-01", "docs/critic-2026-10-01.html", "3", "0"),
    ("stage 8", "critic", "2026-10-02", "docs/critic-2026-10-02.html", "2", "0"),
    ("stage 8", "/codex consult", "2026-10-02", "docs/critic-2026-10-02.html", "2", "0"),
    ("plan", "/grilling + /grill-me", "2026-09-29", "docs/plan-review-2026-09-30.html", "7", "1: pooled panel kept, see page"),
]


def table(rows: list[tuple[str, ...]], header: str, table_id: str) -> str:
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='t' id='{table_id}'>{header}{body}</table>"


def page(
    rows: list[tuple[str, ...]],
    header: str = HEADER,
    table_id: str = "coverage",
    rounds: list[tuple[str, ...]] | None = ROUNDS,
    reviews: list[tuple[str, ...]] | None = REVIEWS,
) -> str:
    log = table(rounds, CHALLENGER_HEADER, "challengers") if rounds is not None else ""
    rev = table(reviews, REVIEW_HEADER, "reviews") if reviews is not None else ""
    return f"<html><body>{table(rows, header, table_id)}{rev}{log}</body></html>"


def pending(rows: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    return [(r[0], r[1], r[2], "pending", "", "") for r in rows]


def swap(rows: list[tuple[str, ...]], item: str, new: tuple[str, ...]) -> list[tuple[str, ...]]:
    return [new if r[0] == item else r for r in rows]


def test_stage4_passes_with_later_rows_pending() -> None:
    problems, counts = cc.check(page(STAGE4 + pending(STAGE8), rounds=None), 4)
    assert problems == []
    assert counts == {"ran": 6, "blocked": 1, "pending": 20}


def test_stage8_passes_when_every_row_closed() -> None:
    problems, _ = cc.check(page(STAGE4 + STAGE8), 8)
    assert problems == []


def test_missing_table_fails() -> None:
    problems, _ = cc.check(page(STAGE4, table_id="other"), 4)
    assert problems == ['no <table id="coverage"> on the page']


def test_header_missing_column_fails() -> None:
    header = "<tr><th>Item</th><th>Kind</th><th>By</th><th>State</th><th>Evidence</th></tr>"
    problems, _ = cc.check(page(STAGE4, header=header), 4)
    assert problems == ["coverage header lacks column(s): reason"]


def test_open_row_due_now_fails() -> None:
    rows = STAGE4[:-1] + pending(STAGE4[-1:])
    problems, _ = cc.check(page(rows), 4)
    assert any("1 week: open" in p for p in problems)


def test_underpowered_is_refused_even_with_a_code() -> None:
    rows = STAGE4 + [("Weather", "driver", "4", "blocked", "", "row-floor: 313 rows, underpowered")]
    problems, _ = cc.check(page(rows), 4)
    assert any("refused reason" in p for p in problems)


def test_blocked_without_code_fails() -> None:
    rows = STAGE4 + [("Weather", "driver", "4", "blocked", "", "new pipeline, user's call")]
    problems, _ = cc.check(page(rows), 4)
    assert any("needs a reason code" in p for p in problems)


def test_declined_needs_a_date() -> None:
    bad = STAGE4 + [("Kpler flows", "driver", "4", "blocked", "", "declined: paid licence, user said no")]
    good = STAGE4 + [("Kpler flows", "driver", "4", "blocked", "", "declined: paid licence, user said no 2026-09-29")]
    assert any("declined: needs the date" in p for p in cc.check(page(bad), 4)[0])
    assert cc.check(page(good), 4)[0] == []


def test_no_data_and_validity_need_evidence() -> None:
    for code in ("no-data: not in crude-db", "validity: project does not trade"):
        rows = STAGE4 + [("Storage", "driver", "4", "blocked", "", code)]
        assert any("needs its evidence" in p for p in cc.check(page(rows), 4)[0])


def test_compute_needs_its_number() -> None:
    rows = STAGE4 + swap(STAGE8, "M6 rung", ("M6 rung", "mechanism", "8", "blocked", "", "compute: too slow"))
    assert any("compute: needs its number" in p for p in cc.check(page(rows), 8)[0])


def test_row_floor_is_refused_on_a_rung() -> None:
    blocked = ("F6 family", "family", "8", "blocked", "", "row-floor: 313 anchors vs 10000 params")
    rows = STAGE4 + swap(STAGE8, "F6 family", blocked)
    assert any("never a reason on a rung" in p for p in cc.check(page(rows), 8)[0])


def test_ran_needs_evidence_with_a_value() -> None:
    for evidence in ("see the target page", "docs/grid-2026-09-29.html", "iter3_experiments.jsonl"):
        rows = swap(STAGE4, "1 week", ("1 week", "horizon", "4", "ran", evidence, ""))
        assert any("ran needs evidence" in p for p in cc.check(page(rows), 4)[0]), evidence
    rows = swap(STAGE4, "1 week", ("1 week", "horizon", "4", "ran", "seed range 3/5 agree", ""))
    assert cc.check(page(rows), 4)[0] == []


def test_missing_required_kind_fails() -> None:
    rows = [r for r in STAGE4 if r[1] != "driver"]
    problems, _ = cc.check(page(rows), 4)
    assert "no driver row due by stage 4" in problems


def test_stage8_needs_every_rung_and_m1_is_not_m10() -> None:
    rows = STAGE4 + [r for r in STAGE8 if not r[0].startswith("M1 ")]
    problems, _ = cc.check(page(rows), 8)
    assert any(p.startswith("no M1 row") for p in problems)
    assert not any(p.startswith("no M10 row") for p in problems)


def test_rung_deferred_past_stage_8_fails() -> None:
    rows = STAGE4 + swap(STAGE8, "F3 family", ("F3 family", "family", "10", "pending", "", ""))
    problems, _ = cc.check(page(rows), 8)
    assert any(p.startswith("no F3 row due by stage 8") for p in problems)


def test_challenger_log_is_checked_from_stage_8() -> None:
    assert any("challengers" in p for p in cc.check(page(STAGE4 + STAGE8, rounds=None), 8)[0])
    undated = [("3", "", "add storage", "missing input", "", "", "")]
    problems, _ = cc.check(page(STAGE4 + STAGE8, rounds=ROUNDS + undated), 10)
    assert "challenger round 3: needs the date it was declared (YYYY-MM-DD)" in problems
    assert "challenger round 3: needs its paired interval" in problems
    assert "challenger round 3: needs its verdict" in problems


def test_reviews_are_due_from_stage_4() -> None:
    assert any('no <table id="reviews">' in p for p in cc.check(page(STAGE4, reviews=None), 4)[0])
    plan_only = [r for r in REVIEWS if r[0] == "plan"]
    problems, _ = cc.check(page(STAGE4, reviews=plan_only), 4)
    assert problems == ["no critic review at the stage 4 gate", "no codex review at the stage 4 gate"]
    by_stage4 = [r for r in REVIEWS if r[0] != "stage 8"]
    assert cc.check(page(STAGE4, reviews=by_stage4), 4)[0] == []
    assert "no critic review at the stage 8 gate" in cc.check(page(STAGE4 + STAGE8, reviews=by_stage4), 8)[0]


def test_only_codex_may_be_not_run() -> None:
    codex_out = ("plan", "/codex consult", "2026-09-30", "", "not run: usage limit, 429 at 09:14", "")
    assert cc.check(page(STAGE4, reviews=[REVIEWS[0], codex_out] + REVIEWS[2:]), 4)[0] == []
    no_reason = ("plan", "/codex consult", "2026-09-30", "", "not run:", "")
    assert "codex at the plan gate: not run: needs its reason" in cc.check(page(STAGE4, reviews=[REVIEWS[0], no_reason] + REVIEWS[2:]), 4)[0]
    critic_out = ("stage 4", "critic", "2026-10-01", "", "not run: busy", "")
    problems, _ = cc.check(page(STAGE4, reviews=REVIEWS[:2] + [critic_out] + REVIEWS[3:]), 4)
    assert any("only codex may be not run" in p for p in problems)


def test_grill_is_due_and_always_runs() -> None:
    no_grill = [r for r in REVIEWS if "grill" not in r[1]]
    assert cc.check(page(STAGE4, reviews=no_grill), 4)[0] == ["no grill review at the plan gate"]
    skipped = ("plan", "/grilling + /grill-me", "2026-09-29", "", "not run: no time", "")
    problems, _ = cc.check(page(STAGE4, reviews=no_grill + [skipped]), 4)
    assert any(p.startswith("grill at the plan gate: only codex may be not run") for p in problems)


def test_review_needs_date_page_and_counts() -> None:
    bare = ("plan", "/plan-eng-review", "", "", "some", "")
    problems, _ = cc.check(page(STAGE4, reviews=[bare] + REVIEWS[1:]), 4)
    for need in ("needs its date", "needs the page", "needs its findings count", "needs its rejected count"):
        assert any(p.startswith("plan-eng-review at the plan gate: " + need) for p in problems), need


def test_implicitly_closed_cells_parse() -> None:
    html = page(STAGE4).replace("</td>", "").replace("</tr>", "")
    assert cc.check(html, 4)[0] == []


def test_main_exit_codes(tmp_path: Path, capsys) -> None:
    good, bad = tmp_path / "good.html", tmp_path / "bad.html"
    good.write_text(page(STAGE4 + pending(STAGE8)), encoding="utf-8")
    bad.write_text(page(pending(STAGE4)), encoding="utf-8")
    assert cc.main([str(good), "--stage", "4"]) == 0
    assert "coverage passes at stage 4" in capsys.readouterr().out
    assert cc.main([str(bad), "--stage", "4"]) == 1
    assert "coverage fails at stage 4" in capsys.readouterr().out
