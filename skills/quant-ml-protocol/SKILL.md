---
name: quant-ml-protocol
description: Rigorous development protocol for predictive models on market/time-series data (small samples, overlapping windows, point-in-time data). Use when building, validating, searching features for, or promoting any forecasting model on financial or time-series data; when running backtests that will be trusted; or when a model verdict ("best", "tied", "promote", "reject") is about to be issued. Enforces pre-registration, process-level nulls, selection honesty, and hard user gates at every promotion decision.
---

# Quant ML Protocol

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
3. **Target decomposition.** Subtract everything the market already pays:
   carry, roll-down, basis. If a naive always-one-side strategy scores well
   on the raw target, the target is wrong, not the model good.
4. **The decision rule, declared.** Which metrics are primary (at least two:
   a ranking metric AND a money metric with costs), what breaks ties
   (parsimony), and what nulls are: vetoes or caution flags. This rule is
   itself attackable at the promotion gate.

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
3. **Selection-honest hold-out**: choose the spec on early years only, judge
   on untouched late years. Report the haircut (as-run minus honest) as its
   own number.
4. Leave-one-year-out; per-feature knockout; seasonality controls (calendar
   dummies alone as a baseline); revision stress on every stored-revised
   driver.
5. **Thin-window rule**: any candidate evaluated on n < 300 anchors goes to
   the pre-registered ACCRUAL LIST with a scheduled re-test date — never
   into the model, never forgotten.
6. **Mandated self-audit** before any verdict: answer "what else is wrong
   with what you did?" with a numbered list of ≥8 findings across data,
   statistics, code, and process — or defend why fewer exist. One pass,
   written down, in the report.

## Stage 6 — THE PROMOTION GATE (hard user gate — never skip)

Promotion, spec changes, and "best model" verdicts STOP here. Present, in
one surface:

1. The honest table (nominate-early / judge-late) AND the as-run numbers,
   side by side, gap stated.
2. EVERY metric with a paired interval — never a single-metric verdict.
   ("All tied" on one metric has been overturned by the money metric.)
3. The decision rule restated, with the sentence: **"This verdict is only as
   good as this rule — attack the rule, not just the numbers."**
4. All caution flags, openly (a null that fails is demoted to a flag only if
   the declared decision rule says so — and it rides every future report).
5. Then ask the user the steering bank's gate questions
   (`references/steering-bank.md` §Gate) and WAIT. Explicitly invite domain
   knowledge the model cannot have: "what market structure, regime change,
   or venue mechanics could explain or refute this?"

No promotion without explicit user sign-off. Being unattended never
authorises skipping the gate — ship the surface as the deliverable instead.

## Stage 7 — prospective discipline (the real judge)

- Append-only ledger: one row per scheduled run, entry recorded at run time,
  judged on its own date, NEVER edited. Old-spec rows are archived and
  labeled, not deleted (deleting one row makes every remaining row worthless).
- Spec tags on every call; a spec change mid-stream is two track records.
- Operational reality is part of the model: what time it runs, what price
  the entry is, what the backtest's marks actually are (settle vs intraday),
  what happens on holidays — measured, not assumed.
- Every surface a consumer sees must have every element explainable
  ("why is this row here?" always has an answer), with honest-limitation
  boxes printed, not hidden.
- Scheduled re-tests for the accrual list; drift monitoring vs the
  backtest's own distribution.

## Cadence of self-audits

Run the Stage 5.6 self-audit: before every verdict, after every campaign,
and whenever the user pushes back on ANY claim (verify first, never defend
first). When the same kind of fix appears three times, stop and fix the
producer, not a fourth instance.

## References

- `references/steering-bank.md` — the human steering-question bank (fire
  them at yourself per stage; fire the Gate set at the user), plus the
  genericized war stories behind every rule above.
- `templates/EXPERIMENT-PROTOCOL.md` — the protocol file to instantiate at
  Stage 0.
