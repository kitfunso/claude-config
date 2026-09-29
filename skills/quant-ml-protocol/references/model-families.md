# Model families, tuning, ensembles

Read at stage 6 (the tuning declaration) and stage 7 (the families). Every
rung runs; a rung stands only by the richer-beats-simpler rule on identical
dates, and a tie promotes the simpler. A rung the sample cannot support runs
as labelled exploratory context and is never skipped. Each id below (F1 to
F6, M1 to M10) is one row of the plan page's coverage table.

## The family ladder

Every family from F2 up runs twice: on the per-refit shortlist, and on the
whole tier 1 set held to the cap. Both are declared before stage 5, with
the cap rule for the tier 1 set and its cut order (the driver-survey rank),
so an empty shortlist still leaves a test of the information.

1. **F1 Champion alone.** The champion specification (one feature or a small predeclared domain baseline), refit per refit date.
2. **F2 Regularised linear.** Ridge, lasso or elastic net;
   regularised logistic for the directional read; linear quantile regression
   for the quantile read. The most stable rung at small samples and where a
   campaign usually ends.
3. **F3 Shallow trees.** Gradient boosting or random forest, shallow by
   default: a depth range centred on 2 to 4 and a leaf floor of one eighth
   of the refit's raw training rows are the initial heuristics, declared
   before Optuna, neither a universal limit; the floor guarantees no count
   of independent observations per leaf. The plan names the library
   parameter and its unit. LightGBM `min_data_in_leaf` (alias
   `min_child_samples`) is an integer count applied through a
   Hessian-based approximation, so a leaf can hold fewer rows; LightGBM
   `min_sum_hessian_in_leaf` (alias `min_child_weight`) is a sum of
   Hessians and is never set from a row count. scikit-learn
   `min_samples_leaf` reads an integer as a count and a float as a
   fraction, `ceil(fraction * n_samples)`, so 0.125 gives one eighth; with
   sample weights the weighted form is `min_weight_fraction_leaf`. Any
   other library: name the parameter and its unit. Row and column
   subsampling, a narrow learning-rate range; monotone constraints where
   the sign of a driver is domain knowledge.
4. **F4 Equal-weight average** of the standing cells across rungs. No fitted
   weights, no extra search, one more cell. Worth running when the
   components' errors differ, not when they are variants of one algorithm.
5. **F5 Stacking.** A declared search on the out-of-fold nomination predictions
   of the base cells, with its own k. Weights are never fitted on judge rows.
6. **F6 Sequence models.** MLP on lags, GRU or LSTM, TCN, patch or attention
   models, TFT for multi-horizon with known-future covariates. Only when (a)
   there is structure the engineered features cannot express and the page
   says what, and (b) the independent-observation count, not the window
   count, supports the parameter count: overlapping windows are not
   independent samples. A few hundred independent observations is a
   warning heuristic, not a hard threshold: the rung is admitted only when
   its effective capacity, regularisation, pretraining and validation
   burden are defensible for the information available; a
   multi-million-parameter model on tens of effective observations is not
   confirmatory, and a small or strongly pretrained model may be when the
   page says why. A cell declared not confirmatory runs as labelled
   exploratory context: it never becomes the standing family or the judge
   candidate, whatever its nomination interval, and the simpler family
   stands. Training: normalisation
   fitted on the training fold; early stopping on an inner purged fold;
   AdamW, dropout or weight decay, gradient clipping; the checkpoint at the
   inner minimum; the declared seed or seed ensemble, with S extra seeds as
   a stability diagnostic (Seeds, below). A joint-horizon model (multi-output or shared head)
   or a recursive multi-step model is admitted here as a separately declared
   family when its structure matches the forecasting problem, under the same
   nomination, null and richer-beats-simpler rules; a recursive family
   accounts explicitly for its accumulated forecast error and uses only
   information available recursively at prediction time. Direct per horizon
   is the default, not a truth.
7. **Probabilistic heads** at any rung: quantile loss for quantiles; a
   parametric negative log-likelihood only when the distribution is
   defensible.

Loss per target: MSE, MAE or Huber for the point change; binary cross-entropy
for direction; pinball for quantiles.

## The mechanism ladder

Restored 2026-09-29 from the grade-diff campaign (2026-09-07), where every
rung below was found untried at once, each "flagged" and none with a row.
The rungs run beside the families at stage 7, round 1 or a later
challenger round, each a declared cell under the grid null.

1. **M1 The level before the sign.** When the target is a level (a spread, a
   differential, a structure) with autocorrelation, AR, ARIMA, exponential
   smoothing or HAR-type models on the level itself. A sign classifier
   stands only beside a level model's row.
2. **M2 Magnitude and distribution.** A regression on the size of the move,
   a volatility model, and a quantile or distributional lane scored by
   pinball loss or CRPS, calibration first. Sizing needs a magnitude; a
   veto (predicting blow-up risk rather than direction) is a cell here.
3. **M3 Window and recency.** Rolling lengths against expanding, and
   exponential recency weights as the continuous version (the stage 7
   grid).
4. **M4 Lag structure of outside data.** Each outside series with declared
   lags, changes, feature windows scaled to the horizon, and interactions
   with regime state, within the cap. One z-score per series is the
   baseline, and the rung starts above it.
5. **M5 Selection with error control.** Decorrelate or cluster first, hold
   the cap, then model-X knockoffs at a stated false-discovery rate,
   generated block-wise for autocorrelated features and labelled nominal.
   Per-feature knockout has no error control and stays a diagnostic.
6. **M6 Structure before search.** Monotone constraints where a driver's
   sign is domain knowledge (LightGBM `monotone_constraints`). Where one
   target is thin and related targets exist (sibling grades, routes or
   markets), partial pooling that shrinks each target's coefficients toward
   the pooled mean by its own standard error: the largest sample-size
   multiplier available.
7. **M7 Tuning.** At least one family tuned by 200-trial Optuna studies
   under the rules below, and a zero-search model beside it (a prior-fitted
   tabular model such as TabPFN, k = 1).
8. **M8 Ensembles across families.** F4 and F5, plus exponential-weights
   aggregation over the live cells as a declared ledger lane: its regret
   bound, of order sqrt(T log N), replaces a champion-challenger pick. The
   row closes at stage 8 on F4, F5 and the lane's declaration; the lane
   runs from the first ledger row.
9. **M9 Late-start data.** A series starting after the sample start runs in
   every window configuration the main cells use, never one, with its
   window-matched null and thin-window status beside each result.
10. **M10 Execution lag and costs.** The trading skeleton's lag and costs
    applied from the first economic read, never dealt at the mid
    (`references/trading-layer.md`). A project that does not trade runs the
    lag half: the forecast scored as of the time the decision can act on it.

The target treatments stage 1 declares (the change, the excess over carry,
the direction, a quantile) and the horizons are coverage rows of their own,
closed by stage 4 once declared with their baselines scored; a challenger
round re-aims the model at one when round 1's error points to it.

## Tuning as a declared search

Before the first trial, on the page: the space, the budget, the seed, the
objective (the primary metric on the inner purged walk-forward, averaged
over inner folds), the stopping and pruning rule, and the retuning
schedule, declared separately from the refit schedule as one of three
designs: retune at every refit; retune on a sparser declared schedule (by
default each refit of the coarsest cadence, with finer cadences reusing
the last study); or tune once on an initial development period, freeze,
and score forecasts only after that period. Hyperparameters used for a
historical forecast come from a study completed using only eligible data
available before that forecast; between retuning dates the last study's
hyperparameters are reused. The trial count is k, and the null replays
rerun the whole search, every study on the retuning schedule, never the
winning configuration alone. Report the fold-to-fold spread beside the mean: one exceptional fold
and several poor ones is a different model from a consistent one with the
same mean. Grid sanity: a rung that collapses the model to the base rate
(over-regularisation) is removed with a note; a winner on a search boundary
triggers a predeclared boundary diagnostic: the space may be widened when
the direction is economically or statistically plausible, and every
widening is one more search-space revision in the flexibility register and
part of the multiplicity burden (no fixed number of widenings). Small
samples: shallow trees, large leaf floors,
narrow ranges. A zero-search alternative (a prior-fitted tabular model such
as TabPFN) has k = 1 and is a fair cell. At least one family is tuned in
every campaign (M7): "a study adds multiplicity the sample cannot pay for"
is refused, because the null replays the study and its cost is a higher
bar, never a false claim.

### Optuna budget

Whenever an Optuna study actually runs, it runs exactly 200 trials
(`n_trials=200`); pruned trials count toward the 200. Between retuning
dates no study runs and no trials are spent: the last study's
hyperparameters are reused. The count is fixed by the protocol,
never chosen from the data or the compute, so the budget is not a degree of
freedom and never moves in either direction. Complexity is controlled
through the search space and the model, never the trial count: narrower
ranges, stronger regularisation, shallower trees, larger leaf floors,
feature caps, and the richer-beats-simpler rule. Small samples still get
200 trials, over a deliberately narrow and strongly regularised space. A
family for which 200 trials is infeasible narrows its space or simplifies
its implementation before the run, or is listed as not fittable. Whether a
study runs once per family and window configuration or once per grid cell,
and on which retuning schedule, is written on the plan before the run; each
study completes on data before the forecasts it serves. Every null replay
that supports a claim from the studies reruns every 200-trial study on the
same schedule in that world; refitting only the real winner's
hyperparameters understates the search and is invalid. The plan states the
null cost as studies per world x B x 200 trials. Deterministic grids keep their enumerated size. Two hundred
trials are two hundred candidate configurations, not observations; they add
nothing to power.

## Seeds

Any stochastic fit (trees with subsampling, nets) declares one seed, or an
ensemble of seeds, and uses it the same way at nomination, in the null, at
the judge read and live; the best seed is never chosen after results. S
extra seeds at the chosen cell, S = 5 by default, more when seed variance
is material, fewer for an effectively deterministic fit, declared before
the stochastic family is compared, are a stability diagnostic: report their
range beside the paired interval. A seed range wider than the interval is
seed noise, said first.

## Feature importance is a diagnostic

Permutation importance and SHAP on the nomination folds feed stage 9: which
features the model leans on and whether that is stable across refits.
Correlated features share importance, so a low number is not absence. Group
knockout (refit without the group) is the inference tool; per-feature
knockout answers "does the model need X", not "does X move the target".

## What sibling campaigns measured (context, not priors)

bd-forecast 2026-08, about 55 independent observations: Optuna over boosting,
nets and Gaussian processes never beat L2 logistic; meta-labelling,
triple-barrier labels, HMM regimes, sequence models and GP classifiers
measured at no gain or a loss against a four-feature logistic; uniqueness
weights at noise level. Each is a cell to include, and a reason to expect
the ladder to end at rung 2 or 3 below a few hundred independent
observations. An expectation predicts the answer; it never skips the rung.
