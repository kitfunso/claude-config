# Model families, tuning, mechanism ideas

Read at stage 1 (the drafts), stage 2 (the study), and at stages 0 and 3 for ideas
worth a row in the pool. A richer model earns its place only by the keep rule on
identical windows; an interval that straddles zero keeps the simpler one.

## Draft families (stage 1)

1. **Regularised linear.** Ridge, lasso or elastic net; regularised logistic for a
   directional read; linear quantile regression for quantiles. The most stable
   family at small samples, and often where a small-sample campaign ends.
2. **Gradient-boosted trees.** LightGBM or CatBoost, shallow at small samples (depth
   around 2 to 4, a large leaf floor). Name the library parameter and its unit:
   LightGBM `min_data_in_leaf` (alias `min_child_samples`) is a row count applied
   through a Hessian approximation, so a leaf can hold fewer rows;
   `min_sum_hessian_in_leaf` is a sum of Hessians and is never set from a row count.
   scikit-learn `min_samples_leaf` reads an integer as a count and a float as a
   fraction. Monotone constraints where a driver's sign is domain knowledge.
3. **Small neural net.** An MLP on lags first. Sequence models (GRU, LSTM, TCN,
   attention, TFT for multi-horizon with known-future covariates) only when there
   is structure the engineered features cannot express, and when the count of
   independent observations, not overlapping windows, supports the parameter count.
   Normalisation fitted inside the fold, early stopping on an inner purged fold,
   weight decay or dropout, the declared seed.
4. **Foundation model, run locally.** Chronos-2 or TimesFM for series, TabPFN for
   tabular, TabPFN-TS in `LOCAL` mode only (its default sends data to the vendor's
   cloud). Zero-shot, so no search. Check the pretraining cutoff against the
   final-read window. On daily financial returns, expect close to a random walk
   (arXiv 2511.18578, 2606.27100): a cheap prior and a baseline, not an expected
   winner. With covariates on an operational target they can tie a tuned model
   (fifty's v3 tied Chronos-2 given the same weather).

Probabilistic heads at any family: quantile loss for quantiles, a parametric
negative log-likelihood only when the distribution is defensible. Loss per target:
MSE, MAE or Huber for the point change; binary cross-entropy for direction; pinball
for quantiles. Horizon strategy: direct per horizon by default; a joint-horizon or
recursive model is its own draft, and a recursive one accounts for its accumulated
error.

## The tuning study (stage 2)

Declared on the campaign page before trial 1: the space, the time cap, the seed,
the objective (the primary metric on an inner purged walk-forward, averaged over
inner folds) and the pruning rule. The study completes on data before the forecasts
it serves; its trial count goes in its ledger row. Report the fold-to-fold spread
beside the mean. Grid sanity: a setting that collapses the model to the base rate
is removed with a note; a winner on a boundary may widen the space once, logged.
Small samples: shallow trees, large leaf floors, narrow ranges, strong
regularisation. Re-tune when the model family changes; feature rounds reuse the
last study.

## Seeds

A stochastic fit declares one seed or a seed ensemble and uses it the same way in
the evaluator, the final read and live; the best seed is never picked after
results. Three extra seeds on final members are a stability check: a seed range
wider than the interval is seed noise, said first.

## Feature importance is a diagnostic

Permutation importance and SHAP on evaluator windows show what the model leans on
and whether that holds across refits. Correlated features share importance, so a
low number is not absence. Group knockout (refit without the group) answers "does
the model need this information"; per-feature knockout answers less.

## Mechanism ideas for the pool

Each is a candidate row in `ideas.md`, with its headroom measured on the slice it
targets.
- **The level before the sign.** For an autocorrelated level target (a spread, a
  differential), AR, ARIMA, exponential smoothing or HAR on the level itself.
- **Magnitude and distribution.** A model of the size of the move, a volatility
  model, a quantile lane scored by pinball or CRPS. Sizing needs a magnitude.
- **Window, recency and refit cadence.** Rolling against expanding, exponential
  recency weights, and online or frequent refits (Jane Street 2024-25, 8th place:
  a daily online update gave +0.008, eight times the next idea).
- **Lag structure of outside data.** Each outside series with declared lags,
  changes and windows scaled to the horizon, and interactions with regime state.
- **Market-level aggregates.** Cross-series means or ranks at each timestamp
  (Ubiquant 1st place: one aggregate lifted CV from 0.141 to 0.154).
- **Target treatment.** The excess over carry, a residual to a reference clock or a
  related series, a re-expressed target that keeps a break outside the window.
- **Structure before search.** Monotone constraints; partial pooling across related
  targets, shrinking each toward the pooled mean by its own standard error.
- **Selection with error control.** Cluster correlated features first, then
  model-X knockoffs at a stated false-discovery rate, labelled nominal for
  autocorrelated data.
- **Late-start data.** A series starting after the sample start runs in every
  window it covers, flagged thin, with a re-test date.
- **The metric itself.** Post-processing read off the scoring rule (Optiver 1st
  place subtracted a weighted mean because the metric is relative).
- **Execution lag and costs.** A project that trades scores the forecast as of the
  time the decision can act on it (`trading-layer.md`).

## What sibling campaigns measured (context, not priors)

bd-forecast 2026-08, about 55 independent observations: Optuna over boosting, nets
and Gaussian processes never beat L2 logistic; meta-labelling, triple-barrier
labels, HMM regimes, sequence models and GP classifiers measured at no gain or a
loss against a four-feature logistic. prc26 2026-09: CatBoost on a residual target
plus an MLP and NNLS blending carried the score; the biggest gains came from
window-state features and outside ADS-B data, not tuning. Each is a draft or an idea
to include, never a reason to skip one.
