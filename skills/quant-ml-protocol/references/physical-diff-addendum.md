# Physical differential addendum

Applies when the target is a physical crude (or product) differential to a
PRA benchmark: grade diffs to Dated Brent, Dubai, WTI Cushing, OSP diffs,
regional spreads. Read with SKILL.md; every rule there still holds. This file
adds what the benchmark mechanics change. Written 2026-09-03 from the
grade-differentials kickoff (crude-db-app docs/research/2026-09-03 brief).

## A. Regime register (Stage 1b — before the first experiment)

A dated table of every benchmark-mechanics change in the sample, declared
before any run, kept in `docs/REGIME-REGISTER.md`:

| date | change | source | effect on target |

Includes: basket composition (grades added/removed), delivery basis (FOB vs
CIF normalisation), QP / de-escalator rule changes, cargo size, assessment
window, sanctions or embargo episodes, PRA methodology notices.

Rules:
- `n_indep` in the protocol is computed INSIDE the current regime. The
  full-history number is reported beside it, never instead of it.
- The selection-honest hold-out sits inside the current regime. A hold-out
  that straddles a regime break tests the break, not the model.
- Every report states which regimes the training window spans.
- Pre-break data may be used only if the target is re-expressed so the break
  does not sit inside it (e.g. grade-vs-grade spread instead of diff to a
  benchmark whose basket changed).

## B. Reset-clean target

PRA differentials contain mechanical steps: monthly quality premiums (QP),
sulphur de-escalators, OSP month rolls, trade-month rolls (Mars, WCS). A
horizon change across a reset is not a forecastable move.

- Strip the published QP / de-escalator / OSP step from the target, or model
  the change with reset days marked and excluded from scoring.
- Never let a reset be scored as a hit. Check: hit rate on reset days alone
  must not differ from hit rate elsewhere.
- Roll-clean applies to the diff's OWN convention (trade month, delivery
  window), not only to the futures leg.

## C. Bounded targets (min / max operators)

When the benchmark is the most competitive grade in a basket (Dated Brent,
Dubai), the cheapest grade's diff is ~0 by construction and every diff is
bounded on one side.

- Record per date which grade is marginal (sets the benchmark).
- Prefer a grade-vs-grade spread (both legs on the same delivery basis,
  freight adjustment applied) to a diff-to-benchmark.
- If the diff-to-benchmark is kept, report results split by "target grade
  marginal" vs "not marginal" days.

## D. Structure decomposition (the physical carry illusion)

There is no forward market in a grade diff, so carry is ~0, but diffs
co-move with prompt structure (CFD / Dated strip). Before any model:

- Regress the horizon change in the diff on the contemporaneous change in
  the structure leg (CFD roll, Dated-vs-forward strip). Report R² and the
  residual s.d. The residual is the forecastable object.
- A model whose signal is explained by the structure leg has found
  structure, not the differential. Name it as such.

## E. Physical expression and cost

A diff forecast is tradeable only through a physical or CFD expression.
Declare it in the protocol: window bid/offer, CFD + cargo, arb-engine route,
or term-lifting nomination. State the cost in $/bbl: demurrage, freight
adjustment, quality escalators, the bid-offer in the window. The money
metric uses that cost from the first backtest.

## F. Data register additions

- PRA assessments: `available_ts` = the PRA `modDate` (or publish time),
  not the assessment date. Keep `isCorrected`; corrections after T+1 are
  stored-revised events.
- Own derived-lake inputs (yield replays, engine restatements, desk marks)
  are stored-revised. Their `available_ts` is the publish run that produced
  the row, and a lag-stress test is required before use as a driver.
- Loading programmes, PRA notices, terminal maintenance: text sources.
  Register them with a capture date; if not captured day-one, they are
  unknown-vintage and cannot be backtested.

## G. Pooled grades and witnesses

Grades sharing one benchmark are one witness, not N. Report per-grade IC
and pooled IC; apply one selection haircut for the pool. A pass on one
grade with the others flat is a flag.

## H. Tripwires beyond statistics

Declare, before the first prospective row:
- Methodology tripwire: any PRA subscriber notice on the benchmark or the
  target grade pauses the lane until the regime register is updated.
- Data-gap tripwire: a missing benchmark or leg row (e.g. an Argus London
  edition lag) skips the row; it does not carry.
- Reflexivity note: entry marks are the next assessment, never our own
  window activity.

## I. Domain baselines (Stage 3 additions)

In the target's own space, on the same anchors: no-change, AR(1) to a
rolling mean, seasonal (maintenance calendar), netback parity (marginal
refinery breakeven from GPW), delivered-parity vs the marginal competing
grade (arb engine). A learned model is declared only if a domain baseline
beats no-change by more than 2×SE in-regime.
