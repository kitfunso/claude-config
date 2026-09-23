# Physical differential addendum

Applies when the target is a physical crude (or product) differential to a
PRA benchmark: grade diffs to Dated Brent, Dubai, WTI Cushing, OSP diffs,
regional spreads. Read with SKILL.md; every rule there still holds. This file
adds what the benchmark mechanics change. Written 2026-09-03 from the
grade-differentials kickoff (crude-db-app docs/research/2026-09-03 brief),
reworded 2026-09-22 to the ten-stage vocabulary; the trading rules moved to
`trading-layer.md`.

## A. Regime register (at stage 2, before any feature is built)

A dated table of every benchmark-mechanics change in the sample, declared
before any run, on the data-audit page:

| date | change | source | effect on target |
|---|---|---|---|

Includes: basket composition (grades added or removed), delivery basis (FOB
vs CIF normalisation), QP and de-escalator rule changes, cargo size,
assessment window, sanctions or embargo episodes, PRA methodology notices.

Rules:
- The independent-observation count is computed inside the current regime.
  The full-history number is reported beside it, never instead of it.
- The nomination and judge years sit inside the current regime. A judge
  block that straddles a regime break tests the break, not the model.
- Every report states which regimes the training window spans.
- Pre-break data may be used only if the target is re-expressed so the break
  does not sit inside it (a grade-vs-grade spread instead of a diff to a
  benchmark whose basket changed).

## B. Reset-clean target (stage 1)

PRA differentials contain mechanical steps: monthly quality premiums (QP),
sulphur de-escalators, OSP month rolls, trade-month rolls (Mars, WCS). A
horizon change across a reset is not a forecastable move.

- Strip the published QP, de-escalator, OSP or trade-month reset effect from
  the target where it is mechanically known; otherwise flag reset days and
  exclude them from the headline forecast score.
- Before that exclusion, report reset-day performance against non-reset days
  as a separate diagnostic, so apparent skill is shown not to come from
  mechanical reset behaviour. A reset is never scored as a hit, and the
  reset-day diagnostic never enters the headline model-selection statistic.
- Roll-clean applies to the diff's own convention (trade month, delivery
  window), not only to the futures leg.

## C. Bounded targets (stage 1)

When the benchmark is the most competitive grade in a basket (Dated Brent,
Dubai), the cheapest grade's diff is about zero by construction and every
diff is bounded on one side.

- Record per date which grade is marginal (sets the benchmark).
- Prefer a grade-vs-grade spread (both legs on the same delivery basis,
  freight adjustment applied) to a diff-to-benchmark.
- If the diff-to-benchmark is kept, report results split by "target grade
  marginal" vs "not marginal" days.

## D. Structure and the differential

Three different things, never one.

D1. Ex-ante adjustment (stage 1, what the market already pays). Subtract
only known contractual or mechanical steps (published QP, de-escalator
and OSP steps, trade-month rolls, section B) and any structure
adjustment for which a predeclared, economically defensible mapping
from information observable at t exists, written on the plan page with
its source. There is no forward market in a grade diff: a carry read
off the CFD or Dated strip is a model, not a quote, and when no
defensible mapping exists nothing is subtracted. This is the carry
line of SKILL.md stage 1.

D2. Ex-post attribution (stage 9). Regress the realised horizon change
in the diff on the realised change in the structure leg over the same
window; report R squared and the residual s.d. A model whose signal is
explained here has found structure, not the differential, and the page
says so. Nothing from D2 changes the target.

D3. Hedged residual target (stage 1, only when the trading page
declares the hedge). If the trade is long the differential and short
beta units of the structure leg, the target is the diff change minus
beta times the structure change, beta fitted per refit on training
rows; both legs' costs sit on the trading page and the ledger scores
the hedged outcome.

## E. Physical expression and cost

On the trading page: `trading-layer.md`, sections on expression and costs.

## F. Data audit additions (stage 2)

- PRA assessments: the available time is the PRA `modDate` (or publish
  time), not the assessment date. Keep `isCorrected`; corrections after T+1
  are revision events that set the source's revision risk.
- Own derived-lake inputs (yield replays, engine restatements, desk marks)
  are grade C (latest-revised history). Their available time is the publish run that produced the
  row, and the declared lag sensitivity (+4 weeks by default) applies before use as a driver.
- Loading programmes, PRA notices, terminal maintenance: text sources.
  Register them with a capture date; if not captured day-one, they are
  grade D (provenance unknown): exploratory or lower-confidence evidence only, never a point-in-time claim.

## G. Pooled grades and witnesses (stages 7 to 9)

Grades sharing one benchmark are one witness, not N. Report per-grade IC and
pooled IC; one selection haircut for the pool. A pass on one grade with the
others flat is a flag, said first.

## H. Tripwires beyond statistics

On the trading page: `trading-layer.md`, tripwires section (methodology
notice, data gap, reflexivity).

## I. Domain baselines (stage 1)

In the target's own space, on the same anchors, beside the constant
baselines: AR(1) to a rolling mean, seasonal (maintenance calendar), netback
parity (marginal refinery breakeven from GPW), delivered parity vs the
marginal competing grade (arb engine). The best of them under the stage 1
primary metric, expressed as oriented primary skill against the relevant
constant baseline, is a champion candidate; whether any domain baseline
improves on the constant baseline is reported on the target page with the
same standardised effect and search-bar logic as the main protocol, and the
campaign continues either way.
