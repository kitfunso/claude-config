---
name: quant-ml-protocol
description: "Building, validating, or promoting a time-series/financial forecasting model: the rigorous nulls/holdout/selection-honesty protocol (model-improve defers here for non-Quantamental work)."
---

# Quant ML Protocol

This is the general protocol. `/model-improve` is its Quantamental
instantiation; it lives in `quantamental/.claude/skills/` and loads only inside
that repo. Use it for the mechanics there, but on any conflict
of statistical principle (nulls, holdouts, selection honesty), this file wins.

Distilled from a real 9-iteration model campaign (Aug 2026): every rule below
was paid for by a specific failure, recorded in `references/steering-bank.md`.
The core insight is a three-tier map of what goes wrong:

- **Known unknowns** — mechanizable: the checklists and gates below. Run them
  unprompted.
- **Unknown unknowns** — partially mechanizable: scheduled adversarial passes
  against YOUR OWN PROCESS (not just the model). Run these unprompted too.
- **Unknown unknown unknowns** — NOT self-generatable. Every catch in this
  tier came from the human: attacks on the decision rule itself, domain
  knowledge the model lacks, "tied on WHAT?" challenges. The skill's job is
  to MANUFACTURE the moments where the human can strike: hard gates with the
  right surface presented and the right questions invited. Never skip a gate
  because the evidence "seems clear" — clear-seeming evidence is exactly what
  the gates exist to attack.

## Stage 0 — before any code: the protocol file

Instantiate `templates/EXPERIMENT-PROTOCOL.md` into the project as
`docs/EXPERIMENT-PROTOCOL.md`. Fill in, in this order:

1. **Sample-size math FIRST.** n_independent = anchors / horizon-overlap.
   SE(IC) ≈ 1/sqrt(n_indep). Write the detectable-effect floor into the
   protocol. Cap features at ~n_indep/8. Every later verdict quotes this
   noise yardstick in the same sentence as its effect size.
2. **Instrument mechanics.** Tenor/contract holdability measured, not
   assumed (a front contract that dies mid-horizon cannot carry the trade).
   Every cost the tradable expression pays — spread, commission,
   financing × calendar days held, borrow — lives INSIDE the net
   primary metric from the first backtest. A known cost carried as a
   caution flag instead of a number has flipped a verdict after
   promotion (AF2 2026: +3.93 bps/day t 2.74 gross became ~+1.13 at
   t ~0.8 once the stated 2 bp/calendar-day financing was applied).
3. **Target decomposition.** Subtract everything the market already pays:
   carry, roll-down, basis. If a naive always-one-side strategy scores well
   on the raw target, the target is wrong, not the model good.
4. **The decision rule, declared.** Which metrics are primary (at least two:
   a ranking metric AND a money metric with costs), what breaks ties
   (parsimony), and what nulls are: vetoes or caution flags. This rule is
   itself attackable at the promotion gate.
   The primary t uses autocorrelation-robust errors (Newey-West or a
   stationary block bootstrap); a plain-SE t on overlapping or
   autocorrelated returns is a diagnostic, never the verdict number.
   Stage 0 is done when every `<...>` placeholder in
   docs/EXPERIMENT-PROTOCOL.md sections 0-3 is a real number or an
   explicit N/A, not before.

## Stage 1 — data honesty

- Every feature row carries `available_ts`; the build FAILS if any feature
  flunks the point-in-time audit. Publication lag is modeled at JOIN time.
- Raw pulls immutable in dated directories; a re-pull is a new directory.
- Record each source's revision status (vintaged / stored-revised / unknown).
  For stored-revised sources: start weekly vintage snapshots on day one and
  stress the top driver with artificial reporting lags NOW, not later.
- Roll-clean any futures/swap series: same-contract changes chained, never
  spliced levels.

## Stage 2 — pre-registration

- Every search is declared BEFORE it runs: axes, cell count, registry hash,
  and the null design that will judge it. An undeclared run is a diagnostic,
  never evidence.
- One immutable primary spec per campaign; variants are labeled diagnostics
  that cannot flip the verdict.
- Every report carries a NOT-DONE table (what was declared but not run, and
  why). Silence about a skipped check reads as "passed."
- **Trial ledger.** Keep a running count N of verdict lanes across the
  campaign — every declared lane that could have produced a pass, plus
  peeks at accruing lanes used to choose the next build. Every pass is
  reported next to N × α (expected false passes) and the expected
  maximum null Sharpe at N trials. A pass inside that noise ceiling is
  a flag, not a result.

## Stage 3 — baselines before models

Random walk, carry/hold, always-long, always-short, coin flip — in the
TARGET'S OWN SPACE, on the same anchors. Plot them on every cumulative
chart. A model that cannot name the naive strategy it beats has no result.

## Stage 4 — model discipline

- Simple → complex, one change at a time, champion/challenger.
- Expanding vs rolling windows: tested, not assumed (small samples usually
  punish forgetting).
- Purge: a training row is admitted only after its outcome RESOLVED before
  the fit date. Remaining overlap gets uniqueness weights.
- Validate the hyperparameter GRID itself (a grid reaching too-strong
  regularization silently shrinks small specs to the base rate).
- A richer model class earns its place only by BEATING the simple one on
  honest rows — a tie promotes the simpler model.

## Stage 5 — the validation gauntlet (adversarial, process-level)

1. **Walk-forward only.** No random splits on time series, ever.
2. **Process nulls, not model nulls**: re-run the ENTIRE recipe — search,
   selection, tuning included — on time-shifted (information-free) inputs,
   ≥20 replays. Compare the real result to the null DISTRIBUTION of the
   process. A wide search manufactures large effects from pure noise; the
   null bar for a search is what the search finds in nothing.
   Fewer kept replays than the declared floor = no null = NO verdict;
   thin the null, lose the lane. Count the null's EFFECTIVE draws:
   placements or replays that share most of their data (e.g.
   overlapping windows on a circular clock) are one draw, not N — a
   p95 over near-duplicates is not a 5% tail. Prefer a stationary
   block bootstrap of the return series when placements must overlap.
3. **Selection-honest hold-out**: choose the spec on early years only, judge
   on untouched late years. Report the haircut (as-run minus honest) as its
   own number.
4. Leave-one-year-out; per-feature knockout; seasonality controls (calendar
   dummies alone as a baseline); revision stress on every stored-revised
   driver.
5. **Thin-window rule**: any candidate evaluated on n < 300 anchors goes to
   the pre-registered ACCRUAL LIST with a scheduled re-test date — never
   into the model, never forgotten.
   The floor counts the anchors the VERDICT statistic rides (judged
   rows after any tune/judge split), not the full sample.
6. **Mandated self-audit** before any verdict: answer "what else is wrong
   with what you did?" with a numbered list of findings covering ALL FOUR
   categories — data, statistics, code, process. A category with no finding
   needs a written one-line defense of why it is clean; there is no minimum
   count (coverage, not quota — a quota manufactures filler findings). One
   pass, written down, in the report.
7. **Independent process critique** before any Stage 6 surface: a
   reviewer that did not build or run the campaign (different agent or
   model, given artifacts not summaries) attacks the method — nulls,
   multiplicity, cost model, selection. Its findings ride the gate
   surface verbatim. The author never reviews alone; the same hands
   authored, ran, and judged everything else.

## Stage 6 — THE PROMOTION GATE (hard user gate — never skip)

Promotion, spec changes, and "best model" verdicts STOP here. Present, in
one surface:

1. The honest table (nominate-early / judge-late) AND the as-run numbers,
   side by side, gap stated.
2. EVERY metric with a paired interval — never a single-metric verdict.
   ("All tied" on one metric has been overturned by the money metric.)
   Include the trial-ledger line: N trials this campaign, expected max
   null Sharpe at N, observed Sharpe beside it.
3. The decision rule restated, with the sentence: **"This verdict is only as
   good as this rule — attack the rule, not just the numbers."**
4. All caution flags, openly (a null that fails is demoted to a flag only if
   the declared decision rule says so — and it rides every future report).
5. Then ask the user the steering bank's gate questions
   (`references/steering-bank.md` §Gate) and WAIT.

Promotion requires explicit user sign-off, every time. Being unattended
never authorises skipping the gate — ship the surface as the deliverable
instead.

## Stage 7 — prospective discipline (the real judge)

- Append-only ledger: one row per scheduled run, entry recorded at run time,
  judged on its own date, NEVER edited. Old-spec rows are archived and
  labeled, not deleted (deleting one row makes every remaining row worthless).
- Spec tags on every call; a spec change mid-stream is two track records.
- **Numeric tripwires at declaration.** Every prospective lane declares,
  before its first row: a REVIEW threshold and a KILL threshold derived
  from the backtest's own return distribution, plus an operational kill
  (skip/error rate). "Judgement stays with the user" gates promotion;
  it is not a substitute for tripwires. A lane too thin to CONFIRM its
  edge at its accrual rate is declared kill-only, with the detectable-
  effect horizon stated.
- Operational reality is part of the model: what time it runs, what price
  the entry is, what the backtest's marks actually are (settle vs intraday),
  what happens on holidays — measured, not assumed.
- Every surface a consumer sees must have every element explainable
  ("why is this row here?" always has an answer), with honest-limitation
  boxes printed, not hidden.
- Scheduled re-tests for the accrual list; drift monitoring vs the
  backtest's own distribution.

## Cadence of self-audits

Run the Stage 5.6 self-audit: before every verdict, and after every campaign.

## References

- `references/steering-bank.md` — the human steering-question bank (fire
  them at yourself per stage; fire the Gate set at the user), plus the
  genericized war stories behind every rule above.
- `templates/EXPERIMENT-PROTOCOL.md` — the protocol file to instantiate at
  Stage 0.
- `references/physical-diff-addendum.md` — READ when the target is a
  physical differential to a PRA benchmark (grade diffs, OSP diffs, regional
  spreads): regime register, reset-clean targets, min-operator benchmarks,
  structure decomposition, physical expression cost, domain baselines,
  non-statistical tripwires.
