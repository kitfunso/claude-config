# Model families, tuning, ensembles

Read at stage 6 (the tuning declaration) and stage 7 (the families). Every
rung earns its place only by the richer-beats-simpler rule on identical
dates; a tie promotes the simpler.

## The ladder

1. **Champion alone.** The champion specification (one feature or a small predeclared domain baseline), refit per refit date.
2. **Regularised linear.** Ridge, lasso or elastic net on the shortlist;
   regularised logistic for the directional read; linear quantile regression
   for the quantile read. The most stable rung at small samples and where a
   campaign usually ends.
3. **Shallow trees.** Gradient boosting or random forest, shallow by
   default: a depth range centred on 2 to 4 and a leaf floor of one eighth
   of the effective rows are the initial heuristics, declared before Optuna
   and scaled to the effective sample, neither a universal limit; row and
   column subsampling, a narrow learning-rate range; monotone constraints
   where the sign of a driver is domain knowledge.
4. **Equal-weight average** of the standing cells across rungs. No fitted
   weights, no extra search, one more cell. Worth running when the
   components' errors differ, not when they are variants of one algorithm.
5. **Stacking.** A declared search on the out-of-fold nomination predictions
   of the base cells, with its own k. Weights are never fitted on judge rows.
6. **Sequence models.** MLP on lags, GRU or LSTM, TCN, patch or attention
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
   page says why. Training: normalisation
   fitted on the training fold; early stopping on an inner purged fold;
   AdamW, dropout or weight decay, gradient clipping; the checkpoint at the
   inner minimum; S seeds. A joint-horizon model (multi-output or shared head)
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

## Tuning as a declared search

Before the first trial, on the page: the space, the budget, the seed, the
objective (the primary metric on the inner purged walk-forward, averaged
over inner folds) and the stopping and pruning rule. The trial count is k,
and the null replays rerun the whole search, never the winning configuration
alone. Report the fold-to-fold spread beside the mean: one exceptional fold
and several poor ones is a different model from a consistent one with the
same mean. Grid sanity: a rung that collapses the model to the base rate
(over-regularisation) is removed with a note; a winner on a search boundary
triggers a predeclared boundary diagnostic: the space may be widened when
the direction is economically or statistically plausible, and every
widening is one more search-space revision in the flexibility register and
part of the multiplicity burden (no fixed number of widenings). Small
samples: shallow trees, large leaf floors,
narrow ranges. A zero-search alternative (a prior-fitted tabular model such
as TabPFN) has k = 1 and is a fair cell.

### Optuna budget

Whenever Optuna is used, the study runs exactly 200 trials (`n_trials=200`);
pruned trials count toward the 200. The count is fixed by the protocol,
never chosen from the data or the compute, so the budget is not a degree of
freedom and never moves in either direction. Complexity is controlled
through the search space and the model, never the trial count: narrower
ranges, stronger regularisation, shallower trees, larger leaf floors,
feature caps, and the richer-beats-simpler rule. Small samples still get
200 trials, over a deliberately narrow and strongly regularised space. A
family for which 200 trials is infeasible narrows its space or simplifies
its implementation before the run, or is listed as not fittable. Whether a
study runs once per family and window configuration or once per grid cell
is written on the plan before the run. Every null replay that supports a
claim from the study reruns the same 200-trial study in that world;
refitting only the real winner's hyperparameters understates the search and
is invalid. Deterministic grids keep their enumerated size. Two hundred
trials are two hundred candidate configurations, not observations; they add
nothing to power.

## Seeds

Any stochastic fit (trees with subsampling, nets) runs S seeds at the chosen
cell, S = 5 by default, more when seed variance is material, fewer for an
effectively deterministic fit, declared before the stochastic family is
compared. Report the seed range beside the paired interval; a seed range wider
than the interval is seed noise, and the cell's claim is the range, not the
best seed.

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
weights at noise level. Each is a cell to include when the sample supports
it, and a reason to expect the ladder to end at rung 2 or 3 below a few
hundred independent observations.
