# Forecast campaign prompt

Use this file for every new forecast model on any energy instrument: a crude or product diff, a
crack, a freight route, a gas or power spread, a time spread or a flat price. Read it first. Then
fill a market sheet from the template in [campaign-markets.md](campaign-markets.md). The worked
examples in that file (CPC, TD3C, jet regrade, B/D) are short summaries; a new sheet fills every
template field. They are examples, not the scope. Every method in
[campaign-methods.md](campaign-methods.md) gets a row in the round's **method table**; each stage
below names its method groups.

## Words this file uses

- **Instrument**: the contract that carries the trade, such as a swap, a CFD forward, an FFA month
  or a future. **Target series**: the series the model forecasts. The two can differ, for example
  an assessment and its swap. A result on a target that nobody can trade is a research proxy until
  the trade is shown.
- **Earned move**: the change in the instrument's price from the fill to the exit, in the
  instrument's quoted unit. It is the default label; the label lab (stage 4) tests the others.
- **Method table**: one row for each method in campaign-methods.md: "run" with its evidence path,
  or "not run because <reason>". A null on another instrument is context, never a reason.
- **Availability time**: the time at which a row could first be read. Keep four stamps on each row:
  the observation date, the publication time, the vintage and the ingestion time.
- **Grade**: A = a true vintage: our saved copies, or a vendor's as-of history proved to be stored
  copies by a stamp check against saved snapshots. An unproved vendor as-of reply is grade C. B =
  restamped from row stamps, or held back by a conservative maximum lag. A revised value read at
  today's level is grade C. It is grade B only when read at its settle lag, the age after which
  saved vintages stop moving. Passing the lag test (B/D G5) never upgrades it. C = history rebuilt
  later with hindsight. Grade C is never confirmatory.
- **Champion**: the current best model. With none, the champion is the best stage 4 reference
  model on own history. **Candidate**: one transformed series from one family. **Family**: one
  driver or one price group, such as free ships, stocks, rival grades or own moves. **Model
  family**: one model class in the zoo, such as ridge or CatBoost.
- **Horizon**: how far ahead a call reaches, in trading days (1 day, 5 days or the natural
  horizon). A target series at one horizon is one **cell** of the search.
- **Nomination rows**: the walk-forward rows before the final span (or before the forward ledger
  starts). Every selection is made on them. Stage 1 sets them.
- **Driver map**: the table of every family, from its mechanism to its data source.
- **Trial ledger**: for every scored trial, the saved per-call predictions, outcomes and losses,
  plus one row in the campaign `results.tsv`. Failed and pruned trials get a row too, and so does
  every Optuna trial. The trial count includes earlier rounds on the same instrument and spans.
- **n_eff**: the effective number of independent calls after overlap. Report it beside every n.
- **Thin window**: a candidate with fewer than 300 walk-forward rows (B/D G4), or with an n_eff
  below 100 (this file's rule for overlapping calls). It is never promoted directly. Show n_eff
  beside the row count.
- **Feature-shift null**: keep the target and the champion real, and shift the candidate's source
  series circularly in time, inside each source's observed span, by at least 26 weeks and not within
  4 weeks of a multiple of 52 (B/D amendment v6, TD3C S7). Linked atoms, such as country imports and
  their total, share one offset drawn from the shortest member's span. It tests whether an add-on
  helps.
- **Target-shift null**: shift the target in blocks at least as long as the horizon, and build
  the own-history features from the shifted target. Use it only for a model built from nothing,
  with no champion.
- **Plant**: a known signal mixed into the target to measure the search's power.
- **NOT-DONE table**: the end of every report. It lists each item that did not run, and why.
- **B/D labels and method codes**: a label with "B/D" before it names a step or rule in
  `bd-forecast/docs/EXPERIMENT-PROTOCOL.md`: G1 to G8 in §0, D0 to D5 in §1 and amendments v2 to
  v4, N1, N2, M2 and the N-null in amendment v5, S1 to S4 in the v5 addendum. Later B/D sections
  reuse some codes for other steps; this file means these. A code without "B/D" (D1, G6, M6)
  names a row in campaign-methods.md.

## Standing rules

1. Declare each round as an appended protocol section, and commit it before the first fit.
   Amendments append. Declared cells stay as written.
2. Track the exposure of every span. Each read of a span is logged. A span that was used to decide
   is spent, and later reads of it are descriptive. Confirmation needs one of two things. Either a
   final span set aside at stage 1 and read once, or a forward ledger with the calls needed, the
   kill rule and the read date set before it starts. After its read, a final span becomes
   walk-forward data for later rounds. The page still shows every read of a spent span, the pick
   and the bar side by side, labelled descriptive; never call a spent span a hold-out (WTI-Brent,
   17 Nov 2026, called its spent rows from 2023 a hold-out and first skipped their read).
3. Report the full record. Decide only on the declared spans.
4. Every number on a page comes from saved results or code.
5. Each stage writes an evidence file (JSON or TSV) and a section of the round page. A "Done when"
   line counts only with the evidence path beside it.
6. Compute budget: time one walk-forward first, then budget each round in hours on this shared box.
   If the plan is over budget, cut in the declared order and list each cut in the NOT-DONE table. If
   the round declares no order, cut tuning of the neural model families (LSTM, GRU, TCN) first, then
   tuning outside the top 5 default model families, then rolling windows other than the best two
   lengths, then cadences other than the best two. Never cut the bank floor, the lag test, the
   poison test, the power test or the null replay.
7. Every walk-forward, at every stage, uses only labels complete by its origin, purges overlapping
   labels and embargoes at least one horizon at each boundary. Every learned step inside a model
   (scaling, imputation, in-model screening, tuning, early stopping) is fit inside the training
   fold. A campaign choice made on nomination rows (bars, label, B/D D0 screen, nomination, trading
   rules) is allowed: the final span never sees it, and the stage 10 null replays each choice that
   picked inputs from the data.

## Stages

### 0. Read what exists

Read this instrument's past work if any, the campaigns on related instruments, the lessons near
the end of this file, and the live desk models that trade this instrument or its legs. Read the
code and results of any desk page already built for this instrument. Methods: O5.
**Done when:** a note lists the past rounds and verdicts, the champion today (or "none"), and the
lessons that apply, each from a file you read this session.

### 1. Trade setup

Record each item with its source.
- The instrument, and the executable price or a defensible proxy for it. An assessment counts as a
  fill price only if the desk can trade at it.
- The decision time, the fill time and the exit time, with the contract mapping and the roll rule.
  Read each leg at its own close; a leg that closes after the call is read from its last close.
- The horizons to test, in trading days: 1 day and 5 days (one week) where the data cadence
  allows, plus the instrument's natural horizon, each with an exact calendar rule.
- A trading calendar with holidays, early closes and clock changes (BST and GMT). Set each short-day
  call time in London time, before that day's close.
- The cost in quoted units per side, never negative: half the spread from dated desk or broker
  quotes, the fee and both legs of each roll. Use a share of price only for an outright price
  level, never for a spread that can sit near zero. Record the clip size that the quotes support.
  Check the book's P&L against a hand-calculated position path for at least 5 calls, one of them
  across a roll.
- The candidate label types (sign or size) and how a forecast becomes a position. Stage 4's
  label lab picks the label.
- Units: the native unit for research tables. Desk pages follow the desk unit rules.
- The nomination rows, and the final span set aside or the forward ledger plan. Size the final
  span so that its n_eff gives 0.8 power at an estimate of the breakeven IC (an IC's standard
  error is about 1/sqrt(n_eff)). If no span can, plan a forward ledger.
- The gate, before any fit: the pick rule, the pass rule, the null statistic and the minimum world
  count. Later amendments cannot change them for this round.
Methods: A, B.
**Done when:** every item has a source, and the calendar and cost rule exist as files.

### 2. Driver map

Walk every class of the **family catalogue** at the end of this file, the fundamental and the
quantitative classes alike. Start each class from the mechanism: why it could move this price.
Add families from desk notes, stage 0, related campaigns and a web scan.
For each family, search the whole source family: the lake table prefix, vendor APIs (with their
as-of options, such as Kpler `snapshotDate`), Platts, LSEG and desk notebooks. Run each vendor's
own example query and try the product's other names before you record "no data".
**Vendor sweep, in round 1.** Before the map is done, list every source the desk can read now:
the accounts and keys in `~/.claude/docs/infra-inventory.md`, every lake schema and table prefix,
Platts, LSEG, and feeds on other boxes (for example Argus on uukmg-ba02). For each vendor, list its
whole catalogue (datasets, endpoints, file families), not only the products the brief names. Mark
each item: pulled, not relevant because <mechanism>, or needs a new licence. Pull every relevant
item in round 1, with its as-of option where one exists. A second round that only adds data reads
the same record twice. A new licence or paid service is Keith's call: record it, do not buy it.
For each source, record its first row, its availability stamps, its revision type (none, revised
or rebuilt) and its grade. Start every source at its first row. Probe each source's open time
against saved snapshots or the vendor's as-of API, and set its maximum lag from the slowest
latency seen across its history. Record the probe in the driver map.
- A revised source stays in: grade C at today's level, grade B at its settle lag (see Grade). Run
  the lag test (lags of 0, 4, 8 and 13 weeks); a pick that uses the source must pass it (B/D G5).
  Save its vintages from today.
- A rebuilt source is grade C. It stays in for research, a pass must hold without it, and a
  re-test on saved vintages is scheduled.
- Stitch a proxy only after an equivalence test on the overlap period and a seam test, with the
  thresholds declared. Report proxy-period results apart from the quoted-target results.
Methods: D, L4.
**Done when:** every catalogue class has family rows or a line "not relevant because
<mechanism>". Every family row ends in "data, first row X, grade Y" or "no data: <what was
checked>". The vendor sweep table lists every vendor and catalogue item with one of its three
ends. Publish the map page, tell Keith and continue. He can stop the run.

### 2b. Data audit

For every source, check bad prints and spike runs (removed at load by a declared rule), duplicate
rows and stale repeats, roll gaps and the roll-date rule, units and conversions, and the same series
from a second vendor (holidays, month-start rolls, level gaps). Compare forward fill with
dropping the row: rows recovered and results changed. Methods: E.
**Done when:** an audit table shows each source with each check passed or the rule that fixed it,
and the rows the fix changed.

### 3. Panel

- Join each row by its own availability stamp. Where no row stamp exists, use a conservative
  maximum lag. A corrected value counts only from its correction time.
- Keep one panel per source with an availability mask, so a late-starting source does not cut
  earlier rows from the other sources.
- Forward fill each source up to its staleness cap, and never use a median fill. A missing flag is
  a declared variant.
- Build every form of every series (B/D N1): level, changes over 2, 4, 8, 13 and 26 periods,
  the change over 52 periods, a 4-period mean, the moving-average spread (4-period less 13-period
  mean), rolling volatility over 13 and 26 periods, and distance from the 52-period high and low.
  Take each as a z-score over 104 and 260 periods. Add the level's percentile rank over the same
  two windows. Use lags 0 to 13 for every form (`bdf3/deepsearch.py`, TRANSFORMS_V7). Add curated
  physical ratios between families, a rolling curve PC1, adaptive trend strength and week-of-year
  harmonics (sin and cos, k up to 2). Rolling z-scores and other trailing forms read only past
  rows, so they may reach back before the training window. Fit every learned step (scalers,
  imputers, PCA, PLS, screens) inside the training fold. Count forms and lags in each source's
  own periods: on a daily panel, lag 1 of a weekly source is one week. Declare min_periods for
  each window. Warm-up rows do not count as scored rows; record each candidate's first scored row.
- Compute regime flags as of the call. Use named regimes only to split the report.
- Use another model's archived live calls (its ledger), from its go-live date. A rebuilt history
  of its calls is grade C.
- Add the other forms in method group F (rank, sign, tercile, spline, PCA and PLS, EWMAs, run
  length, state codes, peer-basket residuals, base-rate lookbacks).
Methods: F.
**Done when:** the poison test passes for every family. The poison test deletes every record
available after the call and asserts that features, forecasts and orders (side and size) do not
change. Check fills apart: each fill is the first print after the latest input opens. Both
checks cover clock-change days, holidays and early closes.

### 4. Bars and default models

Set two bars ex ante, or pick them on nomination rows only.
- **Forecast bar**: the rank IC lower bound must be above zero. A constant forecast has no rank IC.
- **Trading bar**: the best executable simple book, after cost. Candidates: flat, always long,
  own momentum, the last move, a fade, carry, settlement arithmetic where the contract has it, and
  own-history forecasters (statsforecast univariates, SARIMA, Chronos-2, TimesFM). Score a
  pretrained model only on rows after its training-data cutoff; earlier rows are grade C.
Then run the model zoo (stage 7's list) at defaults on the starting set: own history plus the
champion's inputs. On nomination rows, the best linear default and the best nonlinear default
become the two reference models for stage 6.
Run the bars and both reference models over the full **window grid**: an expanding window and
rolling windows of 1, 2, 3 and 5 years (52, 104, 156 and 260 weeks for weekly calls), each crossed
with refit cadences. The cadences are every call, 1 month, 1 quarter and 1 year for weekly calls,
plus every week for daily calls. Every cell counts as a trial, and so does each bar tried.
**Label lab.** Score every label variant in method group C with both reference models on
nomination rows, and pick the label there. Score each variant's forecasts on the earned move, net $
after cost, on the same calls and hold. Every variant counts as a trial. Methods: C, H1, H5, I8.
**Done when:** each target series has its two bars at each horizon, with metrics on nomination rows,
the two reference models (one linear, one nonlinear) are named, a window grid table shows every cell
for each reference model, and the label lab table names the chosen label.

### 5. Power test

Build a causal plant: a signal made only from data available at the call, with the target's
persistence, overlap and missing pattern. Find the breakeven IC by simulation: pass plants of rising
IC through the trading rule and the cost, and take the IC where net P&L crosses zero. Plant at that
IC and at 1.5 times it. Run at least 20 simulations of the frozen search at each size, and 20 with
no plant to measure false hits. A plant counts as found when it is nominated and its B/D D1 paired
gap has a lower bound above zero. Methods: K13.
**Done when:** the page shows the power with its 90% interval, the false-hit rate and the minimum
detectable effect. If the power at 1.5 times breakeven is below 0.8, narrow the search on simulated
data only, declare the cut, and repeat the test. The bank floor stays; narrow the nomination cap,
the B/D D2 set, the scans or the cells. If power stays below 0.8, show it on the page. If it stays
below 0.5, the bank gives leads only: its nominees go to the forward ledger, and no bank nominee
can pass the gate in this campaign.

### 5b. Signed drivers (before the bank)

Take from stage 2 the drivers that have an A or B as-of history and a sign from the mechanism,
about 10 to 30. Commit the sheet (series, sign, form, mechanism) before the first score. Each
driver takes one form by a fixed rule: a level takes its trailing z-score, and a flow takes the
trailing z-score of its change. The composite is the mean of the signed z-scores that a call can
see (`campaign/tier1.py`). Read it once, in the main cell, against the target-shift null.

The read is bound before any score. Freeze the frame (`python -m <campaign>.t1 --freeze`), write
its sha256 in the runner, and commit: that commit is the prereg. The runner then reads only that
frame, from a tree with no uncommitted edit and no code that git does not track. It takes the
file's bytes once, so the frame it scores is the frame it hashed, and a freeze never writes over a
frame that a runner names. A claim uses up the read, with or without a result. If a run fails
after its claim, commit the claim file, then remove it in a second commit that gives the reason.

A sheet with a sign written after scores gives an exploratory read. The size and the direction of
that bias are not measured, so its shift p is no error rate for that record. Its lead is tested on
forward calls only, and it can never pass a model.

The pass mark is a one-sided shift p of 0.04, or lower where labels with no edge pass too often on
this record. Those labels keep the label's trend, vol path and persistence on the paired calls,
and the page shows how many went under 0.04. The read has three outcomes. A pass: on a sheet with
every sign written before scores, the composite is the first candidate for stages 7 to 10; on an
exploratory read, it starts a forward ledger only. No pass: the search on this record stops. That
stop is a rule, not proof of no edge, and the page gives the count of planted edges at the floor
that passed. No answer: the floor search finds no planted rank IC that 80% of the no-edge labels
pass at the mark, so a read that does not pass gives no lead and no stop, and the bank runs
under its own bar. Each driver alone prints beside the composite and decides nothing. A bank
pick needs a p under 0.01.

The rule's lead rates on synthetic records with no edge are in `evidence/tier1/calibration.json`
(`python -m campaign.tier1_null`), for a weekly and a daily cell. The criterion, set before the
run: in each regime the 95% upper bound of the lead rate is at most twice 0.04. The rule was
shaped on that file's seed. `evidence/tier1/calibration-holdout.json` is one run on a second seed,
after the rule stopped changing. Every regime meets the criterion in both files. Two series that drift together pass the plain shift
test. On such a record, and on any record with too few independent shifts, the read has no answer.
**Done when:** the page shows the composite's IC, n_eff, p and mark, the floor (the smallest
planted rank IC that 80% of the no-edge labels pass at the mark), and how many planted edges of
that size passed on fresh labels, with their mean rank IC. The bank's floor is (z(1 - alpha / m) + 0.84) / sqrt(n_eff) for
m candidates.

### 6. Search (B/D D0 to D2)

- **Cells.** Every target series at every horizon from stage 1. A horizon holds only if each
  neighbouring horizon's IC has the same sign at 60% or more of its size; at the grid's ends the
  one neighbour decides (weekly regrade §6, adapted from B/D's neighbouring-lag rule). Windows
  and cadences: the full **window grid** (defined in stage 4).
- **B/D D0 bank and screen.** The bank is every series of every source in the driver map, times
  every form, times every lag. It must hold **at least 10,000 distinct candidates**, the breadth of
  B/D. Stage 3's 14 forms, 2 windows and 14 lags give 392 candidates a series, so the map needs
  about 26 series or more. If the bank falls short, widen the driver map with more families, legs,
  peers and benchmarks. Forms outside stage 3's list, and candidates with no scored nomination rows,
  do not count toward the floor. Report the bank size by catalogue class. Screen each candidate on
  nomination rows by its residual IC: the rank IC against what the champion does not already
  explain. A lag above 0 counts only if its partial IC adds to lag 0. A lag is kept only if each
  neighbouring lag has the same sign at 60% or more of its residual IC (B/D D1); then take the best
  kept lag for each series, form and window.
- **Nominate** the top 2 per family by residual IC, up to a cap of 30 (B/D). Nomination is a rank,
  not a test: the stage 10 null replays it, so it carries the selection. Show a BH table over the
  bank as a descriptive read.
- **B/D D1 parallel add-on.** Score each nominee as champion + 1 against the champion refit on
  the identical rows (the rows where the nominee has data), in every cell, with both reference
  models. Every nominee meets the same fixed champion; the champion does not change during B/D D1.
- **B/D D2 combinations.** Score the pairs of the top 5 nominees, their products with the
  champion's main features and with the volatility regime, and a small declared set of mechanism
  interactions as grouped tests.
- **Selection scans (B/D S1 to S4).** Each one is declared before it runs and is openly a
  selection. Swap trials: the champion less one seat plus a nominee. A subset scan of the
  champion's own features. A best-k search: greedy forward from several starts, then swap polish
  to convergence. An exhaustive scan of every subset of the union of the best specs. All are fit
  on the same rows with one spec. Each winner joins the shortlist, and its backtest edge is
  inflated by construction.
- **Other selectors.** Knockout from the full kept set, lean core plus add-one, permutation
  importance with bands and SHAP, RFE, stability selection, mRMR, Boruta, feature clustering and
  an in-fold top-K screen. When candidates tie inside bootstrap noise, pick the simplest.
- Thin-window candidates get window-matched nulls and a scheduled re-test, never direct promotion.
- **Shortlist** for stage 7: the champion's inputs plus the 5 nominees with the best B/D D1 gaps on
  nomination rows, the best B/D D2 pair, and each scan and selector winner.
Methods: F, G.
**Done when:** the bank holds at least 10,000 distinct candidates, or the page names the shortfall
and the classes that have no data. The page shows the bank size by class, the screen count at each
step and the number of models each scan examined. Every nominee has a B/D D1 row in every cell, or a
NOT-DONE line naming the budget cut that dropped it.

### 7. Model zoo and tuning (shortlist only)

Run the zoo on the stage 6 shortlist: logit, linear SVC, LDA, ridge, RBF and poly SVC, kNN, GP,
naive Bayes, QDA, RF, extra trees, HGB, LightGBM, XGBoost, CatBoost, MLP, LSTM, GRU, TCN and TabPFN
v2. For each model family, declare its output type (sign or size), inputs, position mapping and
tuning space. Record "not applicable because ..." where a model family cannot take the shortlist.
- Run defaults first, over the full window grid.
- Then run Optuna with at least 200 trials for each model family, with the window type, window
  length and refit cadence inside the search space. The objective is walk-forward net $ after cost
  on nomination rows. Check that the objective ranks the trading bar above a flat and a near-flat
  forecast.
- Tune inside each outer fold (nested). Use only labels that are complete by the fold's origin,
  and purge and embargo at every boundary. Stages 8 and 9 read only outer-fold predictions.
  Save each outer year's study as it finishes, so a crash or a stop resumes (WTI-Brent lost 16 GRU
  year studies that only lived in memory).
- Average stochastic models over at least 5 seeds. The seed-noise floor is the 95th percentile of
  the gaps between seeds of one model.
- Run a permutation check: a tuned model reads its inputs only if shuffling them cuts its
  nomination IC by more than the seed-noise floor. Run the noise check too: walk each tuned run
  again with its inputs replaced by seeded noise; a p that moves the same way reads no input.
  For a model with no seed noise, the floor is the gap between two seeded-noise runs. A model
  that reads no input cannot be the pick.
- Add the model designs of group H: GAM, bagged logistic and ARD; regressors on the move mapped
  to p; one model pooled across related markets; a rule in one state and a model in another; the
  agree rule; HMM and Markov-switching regimes.
- Run the tuning checks of group I: the logistic penalty grid (a grid that allows very strong
  penalties can shrink a logit to the base rate; B/D found this and moved to the trim5 grid
  {0.03, 0.1, 0.3, 1, 3}, and TD3C's h = 4 champion had the same fault), time-decay and class
  weights, joint Optuna over inputs, windows and model, and an Optuna bagging study.
- Add the ensembles of group J (mean p, stacking, NNLS, inverse-variance and rank blends, linear
  plus net, subspace bagging, a runner-up ensemble judged as one object) and calibration (Platt or
  isotonic, inside the fold). An ensemble competes for the pick like any run. When it is the pick,
  stage 10 refits all its members as one model, and its trial count is the whole pool it was picked
  from: every scored run of the cell, both tracks, plus the tuned runs and the group H and J runs.
Methods: H, I, J, K12.
**Done when:** every model family has a default row in every window grid cell and a tuned row,
or a reason it does not apply. The page shows each model family's tuned window and cadence.

### 8. Trading layer (before the gate)

On nomination rows, choose the threshold, sizing, hold period, band and roll handling, with a size
cap from stage 1's clip size. Include abstention (B/D M2, method M6): act only when |p - 0.5| is
above a trailing percentile of its own past values. Also score sizing to volatility, a cost filter
(call only where the expected edge beats the cost), conviction thirds, hold until flip, conformal
intervals, and GARCH volatility forecasts for sizing only. Score overlapping positions as one
capital-limited book. Methods: M.
**Done when:** each rule shows net Sharpe, breakeven cost and the worst drawdown, against the
trading bar and always long at equal risk.

### 9. Error map and one mechanism round (before the gate)

Map the errors by regime, state, month and move size on nomination rows. Declare one round whose
design follows the mechanism. Its trials enter the trial ledger. Methods: L2.
**Done when:** the error map is on the page and the mechanism round has a verdict.

### 10. Gate (B/D D3 to D5)

- **Order.** Run the cheap reads first: the gap over the best simple book, each walk-forward year,
  the read without the best year, cost x3 and the lag test. A pick that fails one stops there. Only
  a pick that clears them pays for the null replay.
- **Null.** Use the null statistic declared at stage 1 (B/D used the best full-window paired gap
  from the same pipeline). For an add-on to a champion, use the feature-shift null (B/D D5 and
  N-null). Shift only the atomic source series, each inside its own observed span with its
  availability mask fixed. Then rebuild every derived column (ratios, PC1, spreads) through the same
  code as the real run. The champion's own columns stay real, even when they share an atom with a
  candidate. For a model built from nothing, use the target-shift null. In each world, replay every
  step that chose inputs from the data: the B/D D0 screen, nomination, B/D D1 and D2, the selection
  scans, the other selectors of stage 6, stage 7's joint search over inputs, and the mechanism round
  (refit, not redesigned), with the pick's model family and settings fixed. In the target-shift
  null, replay stage 4 too (bars, label lab, reference models). In the feature-shift null, stage 4
  used only the real target and champion inputs, so it stays fixed. Real and null runs call one
  function, checked by a config hash. Time one full pass P of stages 6 to 9 before the round: (1+N)
  x P must fit the budget for N worlds. If it does not, cut search breadth in rule 6's order, then
  B/D D2 pairs and scans, never the replay scope. SPA and the deflated gap over every zoo trial pay
  for the choice of family and tuning. Check calibration first: on worlds with no added signal, p
  falls below 0.05 in about 5% of runs, and on planted worlds the null finds the plant. Each
  no-signal world needs its own null, so budget the check in the plan or list it as not run. Declare
  the world count N before the null starts: at least 99, and at least 20 times the cells tested, so
  that the Holm-adjusted p can fall below 0.05. With fewer, the null counts as not run and the pick
  cannot pass. Save each world as it finishes, so a crash resumes. Report p = (k + 1) / (N + 1),
  where k is the number of worlds at or above the real score, with its Monte Carlo error.
- **Multiplicity.** Run SPA (`td3c/multiplicity.py`) within each cell and span, on the saved
  per-call loss matrix, and list the columns it drops for too few calls. Compute the deflated gap
  with the effective trial count (`bdf3.scan.eff_dim`), and show the raw count beside it. Use Holm
  across the cells tested. Add PBO by CSCV (the chance that the in-sample best falls below the
  median out of sample), a campaign BH table, Romano-Wolf for families of trading rules, and the
  studentized gap beside the raw gap.
- **Intervals.** Use a paired stationary block bootstrap with blocks at least as long as the horizon
  and as the P&L autocorrelation lasts, a one-sided 90% lower bound and a block-length sensitivity
  check. Report n_eff.
- **Robustness.** Read the results by walk-forward year (each year scored by a model trained on
  earlier rows only), with a purged leave-one-year-out as a description, without the best year, with
  the last two years apart, against the champion on the champion's live-ledger days, at cost x0, x1
  and x3, with a fill one period late, on each fill day, and without the grade-C families. Show long
  and short P&L apart, with long-only and short-only books. For an outright price, also show P&L in
  return terms, because $ scales with the price level; a spread that can sit near zero stays in $.
  Run adversarial validation (how well a classifier tells train rows from test rows) and a learning
  curve. Check that no step falls on a methodology reset day. Show the common-window result beside
  the maximum-history result, and rerun the pick on non-overlapping calls only.
- **Seven checks on every pick** (Keith 2026-11-11, (1)-(6) first run as TD3C round 35,
  `td3c/r35.py`). Declare all seven with the gate and run them on any pick before it goes live:
  (1) ablation: refit with each input dropped alone, each input group dropped whole, and each
  blend or ensemble member dropped, on the same rows, read as the gain against the pick on the same
  calls, Holm in each family; then the lean set (the inputs whose drop costs score), picked on early
  calls and read on later ones; (2) multiplicity: SPA and the deflated gain over every saved trial
  on the same label across all rounds, not only the pick's round; (3) stability: each linear
  member's coefficient sign in each refit (below 80% the same sign is unstable) and the blend
  weights by year; (4) a regime split by vol, curve shape, season, last move and days to expiry,
  where a regime with fewer than 30 calls reads N/A, not a fail;
  (5) the as-of check: the backtest inputs built from data cut at several days equal the full
  build, each live call's stored inputs and score equal a rebuild from today's lake, and a probe
  logs when each live input first opens and whether it stays there; (6) the live ledger read:
  settled live calls apart from rebuilt ones, and the number of calls needed for a verdict;
  (7) the settings sweep: refit at each neighbour of the pick's own settings (regularisation,
  train window, retrain cadence) and with each lookback rebuilt at 0.5x, 0.75x, 1.5x and 2x, one
  setting at a time; declare the share of runs that must score above the null, and never stand in
  a smoothed feature for a rebuilt lookback.
- **The 8 robustness tests** (Keith 2026-11-11: "8 robustness tests" means these, never the seven
  checks above). Run all eight on the pick's book after cost and report each as pass, fail or N/A:
  T1 CPCV/PBO: combinatorial purged cross-validation, with the probability of backtest overfitting
  (PBO); pass when the median Sharpe is above 0, PBO is under 0.30 and more than 60% of the splits
  are positive. T2 Regime: four regimes, high or low vol and up or down trend; pass when at least
  75% of the regimes it can measure are positive; fewer than two measurable regimes reads N/A.
  T3 Param grid: 125 combinations of C, train weeks and retrain weeks; pass when more than 90% are
  positive. T4 Feature grid: shift the lookback of every feature; pass when more than 90% of the
  shifted runs are positive. T5 Ablation: drop one feature at a time; pass when no single drop
  raises the Sharpe by more than 0.01. T6 Annual: pass when more than 80% of the years are
  profitable after cost. T7 Signal decay: enter 2 weeks late; pass when the book keeps more than
  half of its Sharpe. T8 Trade efficiency: pass when net P&L per dollar traded is above 50 bps.
  For a spread, a dollar traded is one spread barrel at the reference leg's settle on the fill day
  (Brent for B/D and WTI-Brent): a long and a short leg carry one barrel of risk, not two. Count
  both legs of a roll.
  Fit each test to the model before it runs (Keith 2026-11-11: "pls properly think about how each
  test should be ran for this particular..." model). Declare the fit in the protocol before any
  score. Run the tests on the book that trades the forecast as it is made (a next-print forecast:
  the sign of p, held one print), and show one lot always long beside each test, so drift does not
  pass for skill. Scale T7's delay to the label: B/D's 2 weeks is 2/7 of its 7-week label, so a
  one-print label is delayed one print; show the literal 2 weeks beside it. Map T3's C, train and
  retrain axes onto the model's own settings (each member's regularisation for a blend). Give T5's
  drops a paired Sharpe interval beside the 0.01 bar, which sits inside the noise of a few years.
- **Code review.** Before the gate read, an outside review (Codex and an Opus reviewer) reads the
  pipeline code. An edit to the shared strategy engine (`sc`, `run.py`, `bt.py`) needs
  `engine_same.py`. An edit to shared forecast code that other campaigns import needs proof that
  every saved result of those campaigns reproduces exactly.
Methods: A3, A5, B1, K, L, O1, O2.
- **Final span.** Freeze the pipeline, the null design and every pass statistic before the final
  span opens. Selection, the null and the robustness design use only rows before it. The scorer
  refuses rows after the cutoff until a committed amendment names the pick. Read the final span
  once and compute every pass item in that one read.
- **Pass rule.** Read on the untouched final span (first read) or the forward ledger, with each null
  world scored on the same span: the forecast IC lower bound is above zero; the net gap after cost
  over the best simple book on that span has a lower bound above zero; for an add-on, the paired gap
  against the champion (IC and net $ after cost) has a lower bound above zero; the null p,
  Holm-adjusted across the cells tested, is below 0.05 (with stage 5b: 0.04 for the composite, 0.01
  for a bank pick); SPA within the pick's cell rejects the best
  simple book at 0.05, and a pick that SPA drops for too few calls cannot pass. Read on the whole
  walk-forward record: every walk-forward year and the read without the best year are positive; the
  result holds without grade C; each revised source in the pick passes the lag test; the pick is not
  thin (at least 300 walk-forward rows and an n_eff of 100 or more), or the thin-window rule
  applies. Keith signs off a causal story (B/D G6); record his words and the date.
**Done when:** a pass table shows each item as pass or fail, with its number and evidence path.

### 10b. Portfolio fit

Read the live books as Portfolio Risk stores them; a book rebuilt from its study can fail on a
stale study (Curve Momentum, 17 Nov 2026), and a failed book is listed, never dropped.
For the pick, show the correlation of its daily and weekly P&L with every live desk book, the change
in the Portfolio Risk book's Sharpe and VaR at the proposed budget, and its position overlap with
live books on the same legs. Split any overlay or hedge gain by its source model before you
recommend it. Apply the desk's risk-budget rule for new models. Methods: N.
**Done when:** the page shows each number against each live book.

### 11. Report and live readiness

Render the round page through the project's existing page code, in the model-report layout, with
metrics against the live book. Show the five highest-Sharpe runs of the search as book columns
beside the pick and the bar, whatever their track, each with its rank and the trial count it came
from; a pick that hides a better run is a reporting fault (WTI-Brent, 17 Nov 2026). End with the
NOT-DONE table (B/D G7). For a pass, show reproducible
evidence before any live use: live and backtest inputs match on the same days; the data and code
versions are pinned; a stale or missing input stops the call; the contract mapping is correct;
and a dry-run book gives the expected position. Methods: O3, O4.
**Done when:** the page is open, the method table has a row for every method in
campaign-methods.md, and the NOT-DONE table lists every item that did not run. A
forward ledger, a live change or a deploy waits for Keith's word.

## Operations

- Run heavy rounds in a worktree. Copy its ignored outputs into the main checkout before you remove
  the worktree.
- Commit named paths: `git commit -F msg -- <files>`. Start no ledger-writing job while another
  session can commit in the same checkout, because a pre-commit stash can wipe its rows.
- Cap the workers and the memory for each worker on the shared box, and keep an Optuna journal
  so a crash resumes.
- Run vendor bulk pulls at their allowed times (LSEG at night only). Kill only the processes of
  your own session.
- Push only on Keith's word.
- Chat gets the outcome in a few short lines. Stage reports go in the page or the protocol.

## Lessons (rule, then where we learned it)

- Read every input as it stood at the call, and fill after the latest availability time. Four
  look-aheads, 3 to 5 Nov 2026: B/D v6 read final revised IIR values and a Kpler pull that live
  never reads; the margin fade filled at the same settle it read; TD3C read a Kpler copy that opens
  the next day; CPC v1 filled at the close it read.
- Map the physical drivers first, and keep revised sources in. TD3C dropped rebuilt ship data.
  Weekly regrade skipped IIR for its short dated history, and daily regrade left out Rystad,
  OilX, Kayrros and EA margins for "no publish time". CPC missed Kpler loadings by querying an
  old grade name. Prices, flows and window data stayed; the physical drivers went.
- Build a wide input bank and screen it on the champion's residual. B/D built every series in many
  forms at lags 0 to 13. Through §11.17, CPC's 145 inputs came in one or two hand-picked forms with
  no lag search; §11.18 searched a deep bank of 18,875 cells on 6 Nov and kept nothing.
- The label can move results more than the data. In CPC v2, at the same timing, tuned CatBoost had
  Sharpe 1.88 from 2022 on the earned move and 2.66 on the last-seen move.
- Take costs from real quotes. TD3C's book charged a fixed 0.25 $/t half spread (`sc/spreads.py`);
  the broker chat's median half spread is 2.78% of price, which evaluator v6 now charges (TD3C
  section 43).
- Compare only matched reads: the same calls, hold and cost. CPC's CatBoost spot and CFD reads match
  at a 1-day hold with no cost (2.66 against 0.81) and at a 5-day hold (1.94 against 1.06).
- Simple rules often win: always long in TD3C, the last move in CPC and the one-year fade in jet
  regrade.
- A wide search buries a real signal. In TD3C, 5,357 noise cells reached an IC of 0.3, so a true
  IC of 0.3 would rank near 5,000th; the planted IC of 0.3 was never found. Run the power test
  first.
- A tuning objective can reward flat models. In TD3C round 17, defaults beat tuning in 13 of 19
  model families.
- One year can make the whole edge. 99% of TD3C's edge came from 2026.
- Seed luck is real. TD3C seed 0 cleared the net bar, and its seed mean did not.
- For add-ons, the target-shift null sets the wrong ceiling. B/D replaced it with the
  feature-shift null (B/D D5).
- Benchmarks change their rules. Platts changed the CPC loading window and its Dated strip on
  2021-03-29 and 2024-04-02 (`cpc/docs/stage0-external-2026-11-04.md`). Put such dates in the
  driver map.
- A shared checkout is fragile. Commit hooks stash other sessions' edits.
- Sweep every vendor before the first bank. Dated Brent round 1 read the lake, Platts and a few
  free sources, and closed null. The round 2 sweep found 18 more pulls (LSEG, Energy Aspects,
  Kpler, IMF PortWatch, OilX, S&P and Signal Ocean) plus Kayrros, so the search ran twice on one
  record (11 Nov 2026).

## Family catalogue

Stage 2 walks every class below, for the instrument, its legs, its peers and its benchmark. The
examples are a start, not a limit.

### Fundamental

1. **Supply**: field and country output, OPEC+ quotas, decisions and compliance, loading
   programmes, export volumes, pipeline flows, terminal and field outages; for gas and power,
   production, LNG sendout, plant outages and wind and solar output.
2. **Conversion**: refinery runs, unit outages and turnarounds, new capacity, yields, margins,
   cracks; for power, the generation mix and spark and dark spreads.
3. **Demand**: imports by buyer, import quotas, stockpiling, transport fuel demand (flights,
   trucking), industrial activity, heating and cooling demand (degree days).
4. **Inventories**: weekly and monthly stocks by hub, floating storage, oil on water, gas storage
   fill, each against its seasonal norm.
5. **Flows and arbitrage**: open or shut arbs, delivered netbacks, arrivals, cargoes in transit,
   tonne-miles, interconnector flows.
6. **Freight and logistics**: tanker rates by route, free ships, ballasters, fleet growth and
   scrapping, port and strait delays, canal limits, bunker prices, war-risk premiums, demurrage.
7. **Quality and rival supply**: rival grade diffs, sulphur and API spreads, official selling
   prices, term against spot.
8. **Policy and shocks**: sanctions, price caps, meeting dates, war and strike flags, counts of news
   events, regulation and carbon rules.
9. **Weather and season**: temperature, storms, fog, monsoon, river levels, the target's seasonal
   norm, holidays.
10. **Benchmark and contract**: methodology changes, assessment window rules, delivery terms,
    quality specification changes, contract launches and liquidity moving between contracts.

### Quantitative

11. **Curve structure**: time spreads (M1-M2, M1-M6, M1-M12), curve level, slope and curvature
    (PCA), carry and roll yield, contango or backwardation state, physical against paper curves.
12. **Price-derived**: momentum and reversal over many lookbacks, z-scores, distance from moving
    averages, breakouts and ranges, realised volatility, skew, drawdown, fractional differences,
    autocorrelation, last step, flat-day runs and the owed move since the last step.
13. **Cross-market lead-lag**: markets that close earlier, related benchmarks, the legs of a spread,
    and the target against its own swap.
14. **Options**: at-the-money implied volatility, its term structure, skew (risk reversals),
    butterflies, implied against realised volatility, put and call volume and open interest.
15. **Volume and open interest**: futures and swap volume, open interest level and change by
    contract, spread volume, block trades, bid-ask spread, trade counts.
16. **Positioning and flows**: COT by trader group, ETF flows, index roll windows, a CTA
    trend-position proxy.
17. **Assessment and microstructure**: window bids, offers and trades, heards, counts of
    participants, partials, flat-day runs.
18. **Macro and cross-asset**: the dollar and key currencies, rates and real rates, breakevens,
    equities (sector and related stocks), credit spreads, VIX, PMIs, China data, metals, dry
    freight indices, gas, coal and carbon.
19. **Forecasts and text**: revisions in agency outlooks (EIA STEO, IEA OMR, OPEC MOMR), analyst
    forecasts, and the tone of market commentary, each with its publication time.
20. **Calendar and events**: expiry and roll days, month end, data release days, meeting days,
    day of week.
21. **Regime**: volatility, trend and curve regimes, HMM states and structural breaks, each computed
    as of the call.
22. **Other desk models**: the calls and probabilities of live desk models, from each model's
    go-live date (its archived ledger), as inputs or ensemble members.
