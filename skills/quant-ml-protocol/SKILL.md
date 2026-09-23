---
name: quant-ml-protocol
description: "Time-series forecasting research (price, spread, freight rate, differential): the staged pipeline from framing to the daily read, each stage closed by a named check with a pass condition. Use when planning, running, reviewing or reading any such model, including a feature screen, a window grid, a judge read, a calibration check or a forecast ledger. Not for cross-sectional or non-temporal ML."
---

# Quant ML Protocol

A research campaign is one HTML plan page in the project's `docs/` and ten
stages, each closed by a named check with a pass condition. The page is the
protocol; there is no separate registry, trial ledger or promotion gate during
research.

Scope: the protocol is optimised for financial, commodity and market time
series. It can be adapted to other sequential forecasting problems, but its
default targets, cadence grid, market baselines and trading layer are
market-oriented by design.

Three questions live in three places and are never one number. Forecasting
(does it predict) is stages 1 to 8. Inference (is the information stable and
interpretable) is stage 9. Decision (does it pay after costs and constraints)
is the trading page. A low-error forecast can lose money; a strong backtest
can rest on one unstable feature.

Revised 2026-09-23 (fifth revision, from the fourth revision's eval
misses). Earlier versions: `~/dev/quant-ml-protocol-draft/old/`.

## Hard rules, defaults and data availability

The protocol separates validity rules from conventions. Chronological
walk-forward evaluation, no known future leakage, fold-local fitting,
selection inside the walk-forward, label purging, one frozen judge read and
search-aware null replay are validity requirements. Point-in-time vendor
history is preferred evidence but is not mandatory: when vintages are
unavailable, use the vendor history with a declared PIT/provenance grade,
revision-risk flag and sensitivity where practical, and do not describe the
result as a fully point-in-time historical backtest. Numerical choices such
as the feature-cap ratio, correlation threshold, null percentile, number and
spacing of null worlds, block length, cadence ladder, seed count and window
tie-break are protocol defaults rather than statistical truths and may be
changed prospectively with the reason recorded. Optuna is the exception:
whenever it is used, the protocol fixes the study at exactly 200 trials.

Hard validity rules, none optional: chronological walk-forward evaluation,
never a random train-test split for a temporal forecast; no known future
leakage; fitted preprocessing inside the training folds; feature, champion,
shortlist and hyperparameter selection inside the walk-forward, on the
declared refit and retuning schedules; purge of labels that have not
matured; the judge block used once, for the frozen specification; no
judge-driven rewrite of the standing specification; search multiplicity
represented in the null replay, the same research search replayed under
it; trading rules never selected on judge P&L; an append-only live forecast
ledger. These protect the research from self-deception.

Defaults are starting points, not statistical truths. A project may change
a default before the relevant search or test runs when the date and the
reason are written on the plan page. Changing a default after observing the
result is a research degree of freedom and is recorded in the flexibility
register. The result is the outcome of the search or test the default
governs (a screen, a null, a grid, a judge read); a look at the inputs
alone, such as feature correlations, missingness or first dates, is not an
outcome, so a change made after it and before that search is prospective.

Blockers and caution flags. A true blocker stops every later stage: known
target leakage, a scaler, imputer or PCA fitted on future rows, unmatured
labels in training, the judge reused for selection, a broken target
construction, invalid split chronology, a null calibration that does not
replay the searched procedure. A caution flag is carried on the page and
the campaign continues: no historical vintages, unknown revision risk, a
small sample, a late-start feature, a coarse null, high seed variance,
unstable regime behaviour, vendor-reconstructed history.

Validity failures found after a result. A verified validity failure
invalidates the affected evaluation regardless of its sign. Preserve the
original result and mark it invalid. Correct the implementation and add a
regression test. A rerun on already inspected judge data may be reported
as a diagnostic correction, but it is not a new untouched confirmatory
test. Confirmation then comes only from fresh matured outcomes, with the
corrected spec running as a labelled challenger on the ledger
(`references/daily-read.md`).

Never cheat time, never select on the judge, never hide search
multiplicity, and never pretend the data is more point-in-time than the
vendor provides. Everything else is a modelling choice, declared, tested
and recorded.

## Three kinds of rule

**Needed by the ML.** Without these the numbers mean nothing.

- Non-stationarity: walk-forward only, never a random split. The model is
  chosen on early years (nomination) and judged once on late years (judge);
  both are named on the plan page before stage 1 closes, together with every
  earlier read that already touched the judge years.
- Leakage: purge (a training row whose label has not matured by the fit date
  is dropped; in a forward-only walk-forward this alone leaves a gap of one
  horizon between the last training anchor and the first test anchor).
  Embargo, a further gap, only where a named mechanism creates contamination
  purging does not remove: a scheme in which later training rows surround or
  follow a validation block (k-fold or combinatorial purged folds, outer or
  inner), or a feature or label construction that spans the boundary. A
  forward-only inner walk-forward with matured labels needs none. The page
  names the mechanism and the gap. Purged inner folds for any tuning; all in
  one place in the code. Every feature row carries the time its inputs became
  available. Anything fitted (scaler, imputer, PCA, calibrator, regime
  labeller, shortlist, champion choice) is fitted at each refit date on data
  to that date; hyperparameters come from a study completed on data before
  the forecasts they serve, on the declared retuning schedule.
- Multiplicity: the bar for a search is what the same search finds when the
  extra information is removed and everything else is kept. The null removes
  the incremental information and keeps the champion's conditional
  structure, the target's support, the clock and the declared regime
  structure, through one adapter per target family
  (`references/targets-and-metrics.md`). For a continuous additive target
  (level, change) the null target is built once over the nomination block:
  the champion's point-in-time forecast plus the out-of-fold champion
  residual (each row's residual from the champion that was live when the
  row was forecast, never an in-sample fit), resampled as one series by a
  method that removes the relationship and keeps the clock. A binary,
  bounded, quantile or distributional target uses a support-preserving
  adapter instead: residuals on the probability or PIT scale under the
  champion, resampled by the same clock-keeping method and inverted through
  the champion's predictive distribution, or conditional simulation from
  it, so null outcomes stay binary or inside the support; an additive
  residual on a probability is never used. The null page shows the residual's rolling scale by
  year beside the regime register and names the method: circular shift or
  stationary block bootstrap when the scale is stable across the block
  (year-to-year ratio under 2, a heuristic default and not a stationarity
  test; another predeclared stability criterion or a formal volatility or
  regime diagnostic may replace it) and no break sits inside it;
  otherwise standardise-and-rescale (the residual divided by a declared
  volatility path, resampled, multiplied back) or resampling within declared
  regimes; a break inside the block means separate claims or a re-expressed
  target, never one global null. Features are untouched, so their
  dependence, the champion's relation and the calendar columns survive, and
  the universe is built once. Each replay reruns the whole procedure
  point-in-time: per-refit champion, per-refit shortlist, any declared
  tuning in full on its retuning schedule (every Optuna study on the
  schedule reruns all 200 trials in each world; refitting only the real
  winner's hyperparameters understates the search and is invalid; the plan
  states the cost as studies per world x B x 200 trials, so 8 annual
  retunes at B = 100 make 160,000 trials per window configuration). The
  statistic is the incremental form of the primary metric
  (`references/targets-and-metrics.md`). One null per claim: b counts the
  replays whose maximum over the search that produced the claim (its family
  and horizon, every cell; for the timing screen both signs, so the
  maximum is over the absolute rank IC, the number the real screen reads)
  beats the real chosen statistic;
  p = (b+1)/(B+1); the campaign-wide maximum is reported beside it as the
  stricter number. The whole-block claim keeps the whole-block null;
  chronology binds in one place, the cutoff used inside the walk-forward
  (stage 5).
- Null worlds: the screen null uses at least 100 distinct valid worlds by
  default, a numerical-resolution default and not a statistical truth: more
  when compute allows or tail resolution matters; fewer are reported with
  the resolution they give, never as a precise p-value. The
  null method is chosen first, by the residual diagnosis above: shift or
  stationary block bootstrap only when the residual scale is stable and no
  structural break sits inside the block; standardise-and-rescale,
  within-regime resampling or separate regime claims otherwise. Circular
  shifts, offsets at least one horizon from zero and two horizons apart by
  default (a spacing against near-duplicate worlds; another predeclared
  spacing may replace it when the dependence structure or sample length
  justifies it), are
  used only when that check passes and the block supplies 100 of them; when
  it does not, B = 200 worlds are generated by the method the same check
  selected (the stationary block bootstrap, block length starting at twice
  the horizon and settled against the empirical dependence of the residual
  by a data-driven selector or a block-length sensitivity declared before
  inference, only where its stationarity holds; the declared
  structure-preserving method otherwise). Sample length decides how worlds
  are generated and how many, never the stochastic assumptions of the null.
  Near-duplicate shifts never pad B. The cutoff is the empirical 95th
  percentile of the replay maxima by default; another predeclared error
  tolerance (90th, 99th) may be written before the null runs, never after
  the real search is seen. It carries the uncertainty its design allows:
  for independently drawn bootstrap
  worlds, an order-statistic bracket whose binomial coverage of that
  percentile is at least the bracket's confidence level (ranks read off
  Binomial(B, q), with q the declared cutoff quantile; the confidence level
  is a separate setting, 90% by default, declared beside q); for a shift
  set, which is one fixed set of worlds and not independent draws, the
  cutoffs from the two interleaved halves of the set as its sensitivity, with
  no coverage claimed; bootstrap worlds whenever an interval is needed. The
  grid null at stage 7 reruns the whole grid per world at B of at least 100
  by the same default;
  when the compute benchmark forbids that, the grid is reduced (fewer
  cells, or a narrower Optuna space, with every study still at 200
  trials) and frozen before the null runs, the real run uses the same reduced grid, and the
  reduced search is replayed at 100 or more; a grid null below 100 worlds,
  never below 20 (a protocol engineering floor), is labelled coarse
  wherever its cutoff or p-value is quoted. Every null is itself a model of
  what the search would find without the incremental information, and its
  validity rests on its resampling assumptions: the null page reports the
  method and the structure it preserves, and where materially different
  defensible nulls exist (volatility regimes, structural breaks,
  heteroskedasticity, binary or distributional targets) it reports the
  sensitivity across them rather than one method as uniquely correct.
- Power: before the real screen, the screen null runs alone and its cutoff
  is compared with the smallest effect worth having, both in standardised
  units. When the effect does not clear the cutoff by the power margin
  (z_power / sqrt(n), rough), the search is underpowered for the minimum
  effect we care about. When feasible, a declared signal-injection check
  measures the power: plant the effect worth having in a real cell, replay
  the whole search, and count the share of worlds where the planted cell
  clears the cutoff actually used. The target is 80%, the declared power.
  Short of it, the universe is shrunk by a dated domain declaration before
  the real screen runs.
- Selection inside the walk-forward: screening, clustering, any fitted
  preprocessing and the champion's identity run at each refit date of the
  coarsest cadence on data to that date, so no nomination prediction uses a
  shortlist or a champion chosen on its own outcomes. Cells with finer
  cadences reuse the shortlist of the coarsest refit before them.
  Hyperparameters used for a historical forecast must come from a study
  completed using only eligible data available before that forecast. The
  retuning schedule is declared separately from the model-refitting
  schedule. Between retuning dates, previously selected hyperparameters may
  be reused.

**Conventions, fixed by choice: defaults, not statistical truths.** Stated
on the page with the date; a project may replace any of them before the
search or test that uses it, with the reason written beside it, and a
change after the result is seen goes in the flexibility register. Horizon
strategy: direct model per horizon by default; joint-horizon and recursive
strategies are separately declared families that compete under the same
nomination, null and richer-beats-simpler rules, a recursive one
accounting for its accumulated forecast error and using only information
available recursively at prediction time. Cluster threshold |rho| 0.9 by
default, declared otherwise before screening; one survivor per highly
redundant cluster in the univariate screen by default, several kept where
domain knowledge or conditional or nonlinear information makes them
economically distinct, the reason declared before stage 5 selection.
Sample counts are
purpose-specific and named, reported separately and never substituted for
one another: n_cap, the effective training rows of the fit in use (rows
after purge and warm-up, times mean label uniqueness, then Kish's effective
sample under recency weights), controls capacity, and the default capacity
guard is Cap = n_cap divided by 8, on clusters, a conservative heuristic
and not a statistical limit (a regularised linear model may carry a wider
set, a shallow tree a tighter one, a strong domain prior a smaller
hand-declared set; the rule in force is frozen before stage 6); n_rank, the
rough overlap-adjusted independent count
(anchors divided by horizon overlap), serves rank IC planning; n_anchor, the
forecast-anchor count with dependence carried by the long-run variance
(block bootstrap or HAC), serves paired-loss metrics. Power and the ledger
minimum use the count that belongs to the primary statistic. Null cutoff:
the 95th percentile of the replay maxima by default, with the uncertainty
its design allows. Screen null at least 100 worlds by default; grid null at
least 100, coarse below, floor 20 (an engineering floor); offsets one
horizon from zero and two horizons apart by default; bootstrap block
starting at twice the horizon in anchors and checked against the empirical
dependence; residual scale ratio 2 as the heuristic warning threshold for
the null-method check. Paired intervals are two-sided at 95% and the power
target is 80% by default, both written before stage 1 closes; at those
defaults z_level = 1.96 and z_power = 0.84. Effects are stated
standardised in the primary metric: a rank IC as itself, with n = n_rank;
a paired-loss metric (MAE, Brier, pinball, CRPS) as the smallest useful
mean paired-loss improvement divided by the long-run standard deviation of
the per-anchor paired differences, estimated on nomination rows as
sqrt(n_anchor) times the block-bootstrap standard error of the mean or by
a HAC estimator, with n = n_anchor and no second division by overlap.
Three rough numbers take the standardised effect e and are labelled rough,
with n the count of the primary statistic: the two-SE bar 2/sqrt(n) for
reading one statistic; the rough analytic search bar
sqrt(2 ln K)/sqrt(n) + z_power/sqrt(n), the expected null maximum of a
search plus the power margin; the ledger minimum
((z_level + z_power) / e)^2, at least 30, which at e = 0.2 gives 196.2, so
197 anchors. That count is a planning approximation, not a universal
formula for rank-IC differences, whole-search maxima or sequential
stopping; a rank IC count is rougher still, and a ledger read by a
confidence sequence takes its count from the sequence's boundary. The
paired block bootstrap is the real uncertainty for all three.
Refit cadence ladder: annual, quarterly, monthly, weekly by default for
daily market data; the project declares another (daily, weekly, monthly;
weekly, monthly, quarterly; event-triggered, monthly) from data frequency,
market mechanics, regime speed and operational feasibility before stage 7.
Recency weighting {none; half-life ladder} is a candidate family, never an
assumption that newer data is better. Revision or availability stress +4
weeks by default for slow fundamental data; a source may instead declare a
lag ladder (+1 day, +1 week, +4 weeks, +8 weeks) from its publication and
revision behaviour, written before its result is read. Staleness cap per
source, set by the source's expected publication cadence and market use (a
forward-filled value older than the cap is missing). Seeds: a stochastic
fit declares one seed, or an ensemble of seeds, and uses it the same way
at nomination, in the null, at the judge read and live; the best seed is
never chosen after results. S = 5 extra seeds at the chosen cell by
default are a stability diagnostic, reported as a range; more when seed
variance is material, fewer for an effectively deterministic fit, declared
before the stochastic family is compared. Optuna budget, the one
user-fixed convention: exactly 200 trials applies whenever a study
actually runs, fixed by the protocol and never chosen from the data or the
compute; between retuning dates the last study's hyperparameters are
reused and no trials run. Space, objective, seed, inner purged
walk-forward, pruning rule and the retuning schedule are declared before
trial 1, and every null replay reruns every 200-trial study on that
schedule (`references/model-families.md`). A tie set above half the grid
means the grid did not discriminate.

**Open, selected on the nomination years, never declared as the answer.**
Expanding vs rolling and the rolling length; refit cadence within the
declared ladder; recency weighting; z-score, change and lag windows; the
feature count within the cap; the model family, including a joint-horizon
or recursive family where declared; the hyperparameters, each set chosen
by a study on data before the forecasts it serves; the target family
beyond the point target. A sibling project's result (bd, wb, td3c) is a
cell to include, not a prior. The selection rule, the tie-break (a declared
complexity score, or the least-machinery order labelled a stability prior)
and the primary horizon are written on the page before the grid runs.

## The stages

Copy `templates/pipeline-plan.html` to `docs/pipeline-plan-<date>.html` and
fill every box before stage 1 starts, the daily-read box with its
append-only ledger and read rule included; a box not yet answerable stays
on the page marked open, never dropped. Each stage row holds the check that
closes it, its state (done, partial or skipped, with the number the check
produced) and where the evidence lives. A true blocker (known leakage,
preprocessing fitted on future rows, unmatured labels in training, the judge
reused for selection, a broken target construction, invalid chronology, a
null that does not replay the searched procedure) stops every later stage,
and one verified after a result was read follows the validity-failure rule
above, whatever the result's sign; a caution flag (no vintages, unknown revision risk, a small sample, a
late-start feature, a coarse null, high seed variance, unstable regimes) is
written on the page and the campaign continues; a negative research result
passes. Nothing downstream starts on a partial
stage unless the gap is written on the page first. The question asked leads;
the stage list serves it. Stages 4 and 5 are discovery (is there information
beyond the champion); stages 6 and 7 are estimation (how a frozen
information set is combined). A search that mixes them pays multiplicity for
both.

1. **Framing, target and power.** Two dated parts: freeze the candidate
   universe and baseline specifications before running outcome-dependent
   comparisons. Part one, declared and frozen before any nomination outcome
   is read: the decision the forecast feeds, in one line. Instrument, horizons and the primary horizon. For a price, spread,
   rate or differential the default point target is the change (log change
   for a positive series, raw change for one that crosses zero), direct per
   horizon by default; the level stays available where the economic
   decision concerns the future level itself, and change is a default for
   this scope, not a universally better target. A directional read and a
   quantile read
   are declared beside it when the decision needs a probability or a size,
   on the same anchors, each with its own metric, never chosen between on
   the judge years (`references/targets-and-metrics.md`). What is subtracted
   because the market already pays it (carry, basis, roll), seam rule,
   roll-clean construction. A residual from regressing the realised target
   on other realised moves over the same window is ex-post attribution for
   stage 9, never a forecast target; a hedged residual target needs the
   hedge declared on the trading page here, beta fitted per refit
   (`references/physical-diff-addendum.md`, D2 and D3). Forecast cutoff time, input snapshot, target mark
   and the scoring metric per target, because the ledger at stage 10 needs
   them. The smallest incremental effect worth having in the primary
   metric, in its raw units (the number that would change the decision),
   the span over which the forecast is worth having (stage 10 reads the
   ledger's reach date against it), and the declared interval level and
   power. Count n_rank per horizon
   (anchors divided by horizon overlap, a rough independent count) and,
   where the primary metric is a paired loss, n_anchor (forecast anchors,
   dependence carried by the long-run variance). Name the nomination and
   judge years and list every earlier read that touched the judge years.
   Specify the required baselines in the target's own space on the same
   nomination anchors as the model: no change, always one side, trailing
   base rate, trailing mean, seasonal naive where a season exists (a level
   target adds AR(1)), and the domain baselines the market suggests. Write
   the champion candidates: a short predeclared list of simple baseline
   specifications with its count; a candidate may be one feature or a
   small frozen domain baseline (seasonal plus carry, curve plus calendar,
   netback plus freight, AR component plus calendar), simple,
   interpretable, predeclared and point-in-time fitted where possible. The
   champion at any refit date is the candidate with the best stage 1
   primary metric (lowest loss, or highest rank IC) on the training rows
   available to that date, as `references/targets-and-metrics.md` defines
   it; it is the one binding comparator, and everything built later is
   judged on what it adds after the champion specification.
   Its identity is chosen inside the walk-forward like every other fitted
   choice, and the full-nomination winner is reported as context, never used
   at an earlier refit. Its fit for the null is named here and matches the
   target family (`references/targets-and-metrics.md`): OLS or fixed ridge
   for a continuous point or level target, the champion's logistic
   probability for direction, the declared quantile regression for
   quantiles, the declared probabilistic champion for a distribution, the
   declared multi-output fit for a trajectory, a support-respecting link fit
   for a bounded target; fitted point-in-time at every refit, and the null
   adapter must match it. When the project will trade the
   forecast, the trading skeleton is declared here and frozen: instrument,
   execution timestamp and expected lag, cost categories, holding rule,
   overlapping-signal treatment, risk limits, the primary economic metric;
   thresholds and sizing are fitted later, on the nomination years only
   (`references/trading-layer.md`). Part two, the outcome reads, dated
   after part one: where the primary metric is a paired loss, the long-run
   standard deviation of the per-anchor paired differences and the
   standardised effect worth having; the required baselines scored on the
   stage 1 primary metric where it applies and on its declared
   secondaries, as `references/targets-and-metrics.md` sets them per
   family, and reported as references that never set a bar (a constant has
   no rank IC and is scored on the loss metrics that apply); the rough
   two-SE bar on the count the primary statistic uses; the rough analytic
   search bar from the planned universe size K in the schema,
   sqrt(2 ln K) / sqrt(n) + z_power / sqrt(n) in standardised units, the
   expected null maximum plus the power margin, labelled rough, beside the
   standardised effect worth having. Pass: the target page carries part
   one, dated (targets, metrics, the raw effect, the span it is worth
   having over, the level and power, the
   counts, the baseline specifications, the candidate list, the null fit
   and, when the project trades, the skeleton), then part two, dated after
   it (the standardised effect, the reference baseline scores, the bars).
   A one-side baseline that scores well is drift the page explains;
   binding skill is improvement over the champion.
2. **Data audit, hygiene and freeze.** Every candidate table in the family,
   found by prefix and directory (list what was not profiled). Per table:
   span, cadence, duplicates, which column is the observation date, rows per
   date (the maximum, not the mean), and a provenance verdict. Point-in-time
   vintages are preferred but not a universal requirement, because vendor
   capabilities differ. Every source gets one grade: A, point-in-time
   verified (historical vintages, archived API or internal daily snapshots,
   a timestamped publication archive, an auditable as-of database); B, a
   historical series with low or limited revision risk but no exact
   vintages (prices, settlements, PRA assessments, exchange data, published
   observations with rare corrections); C, latest-revised history with
   material or unknown revision risk (balances, production estimates,
   inventory models, macro releases, forecast datasets, derived vendor
   models); D, provenance unknown (publication timing, revision behaviour
   and history construction cannot be established). A sources support a
   true point-in-time historical claim. B to D sources may enter the
   research, recorded with PIT status, history type and revision risk; the
   report states the limitation, calls the result a historical backtest on
   vendor-revised history or non-PIT historical evidence, never a fully
   point-in-time backtest, and treats a D-dependent conclusion as lower
   confidence. Where revisions are plausible, a defensible publication-lag,
   revision or stale-information sensitivity runs by the source's declared
   lag rule (+4 weeks by default for slow fundamentals, or a lag ladder)
   when possible. Lack of vintages is a caution flag, not a blocker. What
   stays mandatory whatever the grade: never a feature whose known
   publication date is after the forecast cutoff, never a known future
   observation shifted backward, never a transform fitted on future rows,
   never a judge outcome inside an earlier feature. PIT data is optional;
   known temporal leakage is not. Prove the
   observation date where it is not obvious. Reconcile derived series
   against any published count; a failed reconciliation makes the series its
   own feature, never a splice. Hygiene by `references/data-hygiene.md`: the
   automated
   quality checks, the outlier procedure with every intervention logged, the
   missing-data policy by mechanism with the staleness cap per source, the
   point-in-time availability record per source.
   Universe survivorship: entities, grades, routes, contracts or series that
   left the universe, and whether today's pull still shows them; a universe
   reconstructed from today's list is labelled so.
   Freeze: anchor cutoff, immutable dated raw pulls, a SHA256 manifest that
   later pulls append to, the code commit and the environment lock. Finalise
   K from the exact column counts and the transform ladder, and write the
   universe decision: full enumeration, or a domain shortlist with a one-line
   rationale per row, declared here before any feature is scored against
   the target, with the outcome reads made so far (stage 1, part two)
   listed beside it. Pass: a
   provenance grade and revision-risk label per source, hygiene and
   calendar alignment documented, known future leakage removed, the
   manifest path, K and the universe decision on the plan page, and every
   non-PIT source listed as a caution flag with its sensitivity plan where
   one applies.
3. **Look.** Nomination years only. The target alone: level and changes,
   rolling mean and volatility, autocorrelation, seasonality year by year,
   candidate regimes (volatility terciles, structure sign, known events;
   regime definitions are modelling choices and sensitivity lenses, never a
   claim that the market truly has three regimes),
   missingness through time. The inputs alone: distributions, drift by year,
   missingness, first dates. Stationarity tests are diagnostics for the
   transform choice, never gates. A feature is never plotted against the
   target here; that is the screen, and the screen has a null. Regime flags
   and change-point or HMM labels used as features are fitted inside the
   walk-forward at each refit. Pass: the look page, with no
   feature-versus-target plot on it; any change to the stage 1 target
   written with its reason.
4. **Feature universe.** Enumerated from the schema with exact counts, or the
   declared shortlist; nothing hand-picked after an outcome was read. Every
   numeric column of every admitted table, its provenance grade carried in
   the cell metadata; categorical columns pivoted to one
   series per category, pooled to the K largest plus other above a stated
   cardinality; for every multi-row table a grain table (daily grain, key
   columns, permitted aggregates) written and read once before generation;
   derived series the domain suggests (bucket counts, cross-region spreads
   and ratios, constant-maturity curve points, carry, slope, realised vol,
   a relative-value residual against a related series with its coefficients
   fitted per refit); missingness indicators as cells. Transforms on every
   base series: level, log, changes and z-scores over ladders of windows,
   rolling mean, vol and extremes, exponentially weighted mean, sign and
   streak, trailing-year rank, lags over a ladder, interactions with the
   champion and with a regime flag; seasonality fitted on prior years only;
   calendar dummies and sin/cos day-of-year. Built on the target's calendar.
   Every cell belongs to a named feature group (price history, structure,
   fundamentals, flows, positioning, calendar, missingness) for stage 9.
   Champion candidates are instantiated on the built features; the champion
   identity is selected at each historical refit on training rows to that
   date, and the last nomination-refit champion and the full-nomination
   winner go in the target box as context. Pass: a page listing every cell with table, base series, group, first
   date and cluster, checkable against the schema manifest, each cell
   carrying its source's PIT status; an
   availability assertion: where availability timestamps or vintages exist
   (grade A), a mechanical check that every feature row uses only source
   rows available at or before the anchor's cutoff, by observation date or
   report date as the source's release-date rule says; where the vendor
   supplies no vintages (grades B to D), the best available observation or
   release-date alignment, PIT status recorded as unavailable and the
   declared lag or revision sensitivity applied, with no vintage invented; a
   future-mutation test (appending later source rows changes no earlier
   feature, fitted scaler or prediction), which proves that our own code
   lets no appended row rewrite an earlier engineered feature or prediction
   and never that a vendor's values were unrevised at the original date
   where no vintage archive exists; the per-refit champion identity per
   refit date, and the full-nomination winner's nomination statistic as
   context.
5. **Screen.** First the screen null alone: B replays of the whole screen on
   the null target, offsets spaced as the rule says; the cutoff at the
   declared percentile of their maxima is the empirical search bar and
   replaces the rough analytic one on the plan page. Then, where feasible,
   the signal-injection check: the effect worth having planted in a real
   cell, the whole search replayed, and the share of worlds where the
   planted cell clears that cutoff. Short of the declared power (80% by
   default), or, where injection is infeasible, when the effect does not
   clear the empirical bar by the power margin, the universe decision at
   stage 2 is reopened and rewritten before the real screen runs. Then, at
   each refit date of the coarsest cadence, on data to that date: the
   incremental statistic of every cell against each horizon. Every target
   family has one predeclared one-feature screening estimator, identical
   for every cell and fitted point-in-time at each refit, whose statistic
   is the oriented incremental screening statistic of the target family on
   identical anchors, positive meaning information beyond the champion
   (`references/targets-and-metrics.md`; the oriented primary skill of a
   complete model against the champion is a different object and belongs
   to stages 7 to 10): timing, by default the absolute rank IC of the cell
   against that refit's champion residual, the number the null's maximum
   over both signs reads, with the signed IC kept beside it as a
   diagnostic (a declared alternative learns the sign on the earlier part
   of the refit's training rows and scores the signed IC on the later
   part); magnitude and level, OLS of the champion residual on the
   standardised cell (or ridge at a fixed declared penalty) and paired MAE
   skill; direction, a fixed logistic on the champion score plus the cell
   and Brier skill; quantiles, fixed linear quantile regression per
   declared level and pinball skill; distribution, one predeclared
   probabilistic estimator and CRPS skill; trajectory, one fixed
   multi-output estimator and the stage 1 aggregate horizon score. A screen
   that fits an estimator scores it on a declared forward inner split of
   the refit's training rows: by default, fit on the first two thirds and
   score on the last third, after the purge gap. A fixed OLS screen
   evaluated out of sample on MAE is permissible. Least-absolute-deviation
   regression would align the fitting objective more directly with MAE.
   Whichever fit is declared is the one the null replays.
   The estimator never varies by cell; model-family choice belongs to
   stages 6 and 7. Cutoff at each refit from
   the null rolled to that date: null worlds built on rows to the refit date
   under the same B rule, so the shortlist at a 2020 refit owes nothing to
   2021. The whole-block p-value is a separate number and uses the
   whole-block null. Sign consistency across the nomination subperiods
   seen so far: a cell whose signed diagnostic IC (timing) or incremental
   skill (loss screens) repeatedly alternates between positive and
   negative is flagged unstable even when its pooled score is positive;
   where the one-feature estimator has an
   interpretable coefficient or loading, coefficient-sign stability is
   reported separately as a diagnostic, never substituted for it. One
   survivor per highly redundant cluster by default; several stay where the
   declared reason (domain, conditional or nonlinear information) predates
   this stage. Late-starting columns get a window-matched
   null, a flag and a re-test date, never a claim. Nomination-year numbers
   are selection-inflated and labelled so: they choose, they never claim.
   Pass: a null page recording the target-family null adapter, the
   resampling method with its dependence and regime treatment, B and the
   offset spacing, the residual scale by year, the cutoff with its
   uncertainty, the replay maximum per search and campaign-wide, the
   signal-injection power or the reason injection was infeasible, and the
   pass count; a ranked shortlist per refit date with the incremental
   statistic, the per-refit rolled cutoff, group, cluster and first date.
6. **Selection, cap and tuning rules.** Default capacity guard: Cap per
   window rung = n_cap divided by 8, on clusters, the champion
   specification counted as one (n_cap: effective training rows after
   purge and warm-up, times mean label uniqueness, then Kish under recency
   weights; a capacity count, never the power or ledger count). The ratio
   is a conservative heuristic, not a statistical limit: the project may
   declare another capacity rule before this stage from model family,
   regularisation strength, feature correlation, effective sample and
   domain structure (a regularised linear model may carry a wider set, a
   shallow tree a tighter one, a strong domain prior a smaller hand-declared
   set), frozen before the model comparison. Trees carry a separate depth
   range and leaf floor written on the page, shallow by default, declared
   before Optuna: depth centred on 2 to 4, and a leaf floor of one eighth
   of the refit's raw training rows as the initial heuristic, which
   guarantees no count of independent observations per leaf; the plan
   names the library parameter and its unit (`references/model-families.md`).
   Purge and embargo in the dataset builder only. Any hyperparameter
   search is declared before its first trial: space, budget, seed,
   objective, the inner purged walk-forward, the stopping and pruning rule,
   and the retuning schedule, one of three designs: retune at every refit;
   retune on a sparser declared schedule (by default each refit of the
   coarsest cadence, the dates the shortlist already uses, with finer
   cadences reusing the last study); or tune once on an initial development
   period, freeze, and score forecasts only after that period. Each study
   completes on data before the forecasts it serves. Its trial count is its
   k and the null replays rerun every study on the schedule, never the
   winning configuration alone. Optuna runs exactly 200 trials whenever a
   study actually runs, pruned trials included; a refit between retuning
   dates reuses the last study and runs no trials; a deterministic grid
   keeps its enumerated size; a family for which 200 trials is infeasible
   narrows its space or is listed not fittable, and the trial count never
   moves. The calibration of a probability output is declared here too: no
   additional calibration, Platt, or isotonic. Choosing no calibration is
   admissible when the model already outputs a probability; a raw
   classifier score is never reported as a probability. A calibrator is
   fitted on held-out inner predictions at each refit, never on the
   classifier's own training predictions, and belongs to the cell in the
   grid, the null, the judge read and live. A grid rung that collapses the
   model to the base rate is removed with a note; the fold-to-fold spread
   is reported beside the mean (`references/model-families.md`). Pass: a
   test that purge holds at every outer and inner boundary for every
   cadence in the grid and that each declared embargo holds where it was
   declared; the cap arithmetic written per window rung; the leaf-floor
   parameter and its unit for every tree family; the tuning declaration on
   the page, naming its retuning design beside the study count of all
   three designs (a compute limit is a written trade between them, never a
   design dropped unseen), with Optuna trials = 200 for every
   study that runs; the calibration choice for every probability output.
7. **Model comparison and the window grid.** Families in a ladder
   (`references/model-families.md`): champion alone; a regularised linear
   model on the shortlist (logistic for the directional read, quantile
   regression for the quantile read); shallow trees; the equal-weight
   average of the standing cells, which has no fitted weights and no extra
   search; stacking and sequence models only under that file's rules. Each
   family over the declared grid: window {expanding; rolling ladder} x refit
   cadence {the ladder declared before this stage; annual, quarterly,
   monthly, weekly is the default for daily market data} x recency weight
   {none; half-life ladder}, recency weighting a candidate family and never
   an assumption that newer data is better, per horizon, nomination years
   only, naive and champion baselines in every cell. Cells are ranked on a frozen common set of
   forecast dates per horizon; cells that cannot cover it are reported in
   their own table. Compute is benchmarked on one full replay before the
   run; when it forbids a grid null of 100 worlds, the grid is reduced
   (fewer cells or a narrower space, never fewer trials) and frozen before
   the null runs and the real run uses the same reduced grid;
   the null replays rerun the whole grid. An Optuna-tuned family enters the
   grid with the hyperparameters from its declared 200-trial inner studies;
   whether a study runs once per family and window configuration or once
   per grid cell is written on the plan before the run, never decided after
   results; either way each study completes on data before the forecasts it
   serves, on the declared retuning schedule, and the null replays rerun
   the studies the same way. A stochastic fit forecasts with its declared
   seed or seed ensemble; S extra seeds at the chosen cell are a stability
   diagnostic, their range reported beside the paired interval, and a seed
   range wider than the interval is seed noise, said so. Selection rule:
   highest nomination oriented primary skill against the champion on the
   primary horizon, with the orientation `references/targets-and-metrics.md`
   declares (positive means improvement over the champion); every raw
   primary metric is reported beside it and never selects. Tie rule: for
   every candidate cell, the paired block-bootstrap interval of its
   oriented primary skill minus the best cell's, on identical forecast
   dates; a cell whose paired-difference interval contains zero is in the
   tie set, the flat surface, and the overlap of two separately computed
   intervals is never the test; the tie-break, written
   before the run, picks one cell per family: either the lowest declared
   operational and model complexity score (refits, recency weighting,
   window length, compute), frozen before the grid, or the fixed order of
   least machinery (fewest refits, no recency weight, longest window),
   which leans to expanding by construction and is labelled a stability
   prior, never a statistical rule; the tie set is reported as a set and as a
   fraction of the grid, and above one half the page says the tie-break
   selected, not the data. A richer family earns its place only when the
   paired interval of its oriented primary skill improvement over the
   simpler family clears zero on identical forecast dates; otherwise the
   simpler family stands. A cell declared not confirmatory (an oversized
   sequence model, `references/model-families.md`) never earns it. Raw IC, loss or metric differences never enter
   that comparison directly; everything is converted to oriented skill
   first. The family that stands here is
   the standing family; its cell is the judge candidate. Pass: a surface
   page with every cell's paired interval against the champion, the null
   grid, the chosen cells, the tie set and the standing family.
8. **Judge read.** Freeze first, on the page: feature definitions, the
   shortlist rule, the cap, the tuning procedure and its retuning schedule,
   any calibrator, the standing family and its cell, the refit cadence,
   and the economic rule, when the project trades. The standing family's
   cell runs once on the judge years and that read is the result; the other
   families' chosen cells run once too and are context, labelled so. Report
   the judge oriented primary skill against the frozen champion rule (the
   champion as selected at each refit on data to date, rolled through the
   judge years the same way), its paired interval, and the selection
   haircut, defined as nomination oriented primary skill minus judge
   oriented primary skill, as its own number with the judge sample's own
   uncertainty: positive means the judge years came in worse than
   nomination, negative means better. The raw primary metric is reported
   beside the skill. The tie set is reported on the
   judge years as a range, never
   chosen from. A regime split (a cell that wins only in the latest year) is
   a finding, never the selector of the live spec. No second look: a
   disappointing judge read is the result, and any change informed by it
   needs fresh outcomes before it can be confirmed. A verified validity
   failure follows the validity-failure rule at the top whatever the sign:
   the read is kept and marked invalid, a rerun on the same judge years is
   a diagnostic correction and never a new confirmatory test, and the
   corrected spec confirms only on fresh matured outcomes as a labelled
   challenger. Pass: the judge page with the freeze list.
9. **Error analysis, calibration and stress.** Nomination and judge reads
   split by year, regime flag, volatility tercile, month and horizon;
   residual bias and autocorrelation; predicted against actual;
   deterioration over time. Calibration diagnostics by
   `references/targets-and-metrics.md`: the directional read gets a
   reliability diagram, Brier and log loss, with the base rate's as a
   reference; the quantile read gets coverage per level and pinball loss.
   Nothing is fitted here: the calibration choice was declared at stage 6
   and is part of the frozen spec.
   Stability, the inference question: knockout per surviving feature and per
   feature group; sign stability of coefficients or importances across
   refits; permutation importance and SHAP are diagnostics on nomination
   folds, never selectors. Stress: revision or lag sensitivity on every
   admitted B to D source by its declared lag rule, reported as non-PIT
   historical evidence; outage masking per feature group (the spec runs with a
   group missing, or the page says it cannot); the seed spread; adversarial
   validation (a classifier separating nomination rows from judge rows on
   the features), whose AUC is expected high for time blocks, so the output
   is the list of separating features, each of which gets a knockout. Stage
   9 may explain the judge result, never rewrite it: nothing learned from
   judge-year outcomes here changes the standing spec, its shortlist, its
   calibrator or its cadence; a judge-derived idea (drop feature X, add a
   regime gate) becomes a labelled challenger under the daily read's
   challenger rule and claims only on fresh matured outcomes, and it is
   never scored on the judge years that suggested it, not even as a
   diagnostic, because that read is a second look; knockouts of the frozen
   spec on the judge years are attribution, never selection. Pass: the regime page;
   a regime-only winner labelled on the plan page; the outage behaviour
   written.
10. **Write-up, then the daily read.** One HTML page: target, baselines, the
    enumerated list of what was covered and what was not, the grid, the judge
    read, the calibration, the regimes, the caution flags in force, the
    researcher-flexibility register (targets tried, universes tried, grids
    run, search spaces tried and revised with every boundary widening
    counted, families tuned, defaults changed and whether before or after
    the result, protocol changes with dates, judge exposures, post-hoc
    hypotheses; the Optuna trial count is protocol-fixed and is not a
    degree of freedom),
    the regenerate commands, the next stage. No promotion, no shipping. Then
    the daily read by `references/daily-read.md`: it starts only if the
    standing
    family beat the champion on the judge read (else the champion alone
    runs, or nothing, and the page says which); the live spec is the frozen
    cell rolled forward at its cadence, trained at each declared refit date
    on the eligible rows within its selected window and retuned on its
    declared retuning schedule; one code path builds research and live
    features, proven by the consistency test on the first run; every run
    writes one immutable forecast row carrying all three ids (spec_id,
    fit_id, forecast_id; a scheme with fewer is incomplete), the cutoff
    time, input snapshot hash, prediction, and the champion's forecast with
    its fit_id; every matured target writes one outcome record linked to
    it, nothing edited.
    The read rule is written before the first row: the statistic, the
    minimum matured outcomes, the date the ledger reaches that minimum at
    its accrual rate, and either a confidence sequence or one fixed read
    date. Beside the reach date the page says whether the ledger can
    confirm skill: when the date falls past the span the forecast is worth
    having (stage 1), the ledger is kill-only, able to detect decay and
    never to confirm skill. A glance at the ledger is allowed daily, a claim from it is
    not until the rule holds. Monitoring, the challenger rule, the fallback
    spec and its triggers are declared there too. The ledger is the last
    stage of research and the only judge of the model from then on. Pass:
    the report page, the read rule and fallback on the plan page, the first
    ledger rows.

A trading layer, when a project has one, is its own page after stage 10 by
`references/trading-layer.md`: expression, costs, execution lag, sizing,
overlapping signals, tripwires; its economic rule is frozen before stage 8
opens. It never sits inside the research metric.

## Reporting rules

- "Done" is a claim about the stage list: every stage reported as done,
  partial or skipped, with the check that passed. Never "tried everything",
  "every table" or "all features" without the enumerated list on a page.
- Call data absent only after searching the whole family (table prefix,
  directory). Read every reference artefact in full before summarising it.
- Null, flat or worse than the champion is said first, with no softening
  frame. Effect size and its bar live in the same sentence; "best", "dead
  weight" and "top driver" are banned without the bar.
- A result that depends on a B to D source is a historical backtest on
  vendor-revised history, or non-PIT historical evidence, and is named so;
  "what the model would have known in 2018" is written only where every
  input is grade A.
- The cutoff, the cap, the window, the tie-break, the primary horizon, the
  tuning space, seed, objective, stopping rule and retuning schedule, and
  the read rule are stated before the run that uses them, on the page, with
  the date; the tuning budget is fixed at 200 Optuna trials whenever a
  study runs.
- When the user pushes back on a claim: verify first (re-read, re-run,
  re-grep), never defend first; concede to evidence at once.
- Two methods optimising the same metric on the same rows are one witness,
  not two. Grades or routes sharing one benchmark are one witness.
- No "shipping", "promotion" or "deploy" in research; the daily read with its
  ledger is the last stage.
- If the same kind of fix appears a third time, stop patching and fix the
  producer.
- Chat stays short and plain; the page carries the numbers.

## Reference implementations (reuse the machinery, never the results)

- td3c-forecast `docs/pipeline-plan-2026-09-22.html`: the page shape, the
  stage 2 audit and freeze, the window grid, the cap arithmetic, the drift
  monitor; `docs/plan-review-2026-09-22.html`: the two-reviewer review.
- bd-forecast `src/bdf3/deepsearch.py` (atlas, nominate, wf_delta: series x
  transform x z-window x lag cells with IC and partial IC, lag-neighbour sign
  consistency, paired block-bootstrap delta), `src/bdf/search/transforms.py`,
  `src/bdf/dataset.py` (purge in one place).

## References

- `references/targets-and-metrics.md`: target families, the metric per
  target, calibration and coverage checks. Stages 1, 6 and 9.
- `references/data-hygiene.md`: quality checks, outliers, missing data,
  alignment, the freeze manifest. Stage 2.
- `references/model-families.md`: the family ladder, tuning as a declared
  search, seeds, ensembles, sequence models, importance as diagnostics.
  Stages 6 and 7.
- `references/daily-read.md`: the live spec, the run, consistency,
  versioning, the ledger and its read rule, monitoring, challenger and
  fallback. Stage 10.
- `references/trading-layer.md`: the trading page. Money never enters the
  research metric.
- `references/steering-bank.md`: questions to fire at yourself per stage and
  to present with the write-up, with the failures that earned each one.
- `references/physical-diff-addendum.md`: read when the target is a physical
  differential to a PRA benchmark.
