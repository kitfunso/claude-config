# Targets and metrics

Read at stage 1 (declaring the targets and their metrics), stage 6 (the
calibration choice) and stage 9 (calibration diagnostics). Every target
declared here is scored on the same anchors, the same folds and the same
frozen forecast-date set as the point target.

## Target families

| | Target | When it fits |
|---|---|---|
| A | Level, S at t+h | The future level itself matters (storage, load). Carries the unit root; baselines add AR(1) and exponential smoothing on the level. |
| B | Change, S at t+h minus S at t; log change for a positive series | The default point target for a price, spread, rate or differential. |
| C | Direction, 1 if the change is positive | Declared beside B when the decision is a side. Binding skill is against the champion; the trailing base rate is the reference, never 50%. |
| D | Trajectory, S at t+1 to t+h | Only when the path matters, not the endpoint. Multi-output. |
| E | Distribution of S at t+h given X at t: quantiles or a parametric head | Declared beside B when the decision needs a size, an interval or a tail. |

Rules. B is the default point target for this skill's price, spread, rate
and differential scope, a default and not a universally better target; A
stays available where the economic decision concerns the future level
itself, and the plan page says which. C and E are
declared beside B, never instead of it; each has its own metric and its own
null replay; nothing is chosen between them on the judge years. A directional
read that beats its base rate while the point read is flat is a finding to
report, not a switch of target.

Horizon strategy: direct, one model per horizon, is the default. A
joint-horizon model (multi-output or shared head) and a recursive
multi-step model enter as separately declared families when their
structure matches the forecasting problem, and compete under the same
nomination, null and richer-beats-simpler rules. A recursive family
accounts explicitly for its accumulated forecast error and uses only
information available recursively at prediction time.

## The metric per target

| Target | Primary | Secondaries | Reference baselines (reported) |
|---|---|---|---|
| Point change, timing decision | rank IC | MAE, sign hit | no change and trailing mean, on MAE (a constant has no rank IC) |
| Point change, magnitude decision | MAE, with relative_mae (model MAE over no-change MAE on the same rows); Huber where the page says why | rank IC, sign hit | no change, trailing mean |
| Direction | Brier | log loss, balanced accuracy, reliability diagram | trailing base rate, majority side |
| Quantiles | pinball loss per level | coverage per level | the unconditional quantiles of the training rows |
| Distribution | CRPS | coverage of the central intervals | the unconditional distribution |
| Level | MAE, MASE (MAE scaled by the in-sample one-step naive MAE, Hyndman and Koehler 2006; a ratio to an out-of-sample same-horizon baseline is always called relative_mae) | RMSE | naive last value, AR(1) |

The champion is always the binding comparator, for every target (oriented
primary skill, below); the reference baselines are reported beside it and
never set a bar.

Brier, log loss, pinball and CRPS are proper scoring rules: a forecaster
minimises them by reporting what it believes. Accuracy and sign hit are not,
so they stay secondaries. Every comparison carries the paired block bootstrap
interval on identical anchors; a Diebold-Mariano test on the same paired loss
differences, with autocorrelation-consistent errors, is the parametric
equivalent and is reported beside it when a reader expects one.

Predicted quantiles are non-crossing: the fit enforces monotone quantiles,
or one predeclared monotone rearrangement or isotonic correction is
applied. The crossing rule is fixed before the first screen and replayed
identically under the null.

Rule: the primary metric follows the decision declared at stage 1. The
null statistic and the screen's ranking use the primary metric's
incremental form, the oriented incremental screening statistic: the
target-family statistic of one predeclared one-feature estimator over
the champion on identical anchors, positive meaning information beyond
the champion, the same estimator for every cell, fitted point-in-time
at each refit. A screen that fits an estimator scores it on a declared
forward inner split of the refit's training rows: by default, fit on the
first two thirds and score on the last third, after the purge gap. The
stage 7 selection rule uses the oriented primary skill of a complete
model, defined below. Screening estimator per family: timing, no fitted
model, by default the absolute rank IC of the cell against the champion
residual, the number the null's maximum over both signs reads, with the
signed IC kept beside it as a diagnostic (a declared alternative learns
the sign on the earlier part of the refit's training rows and scores the
signed IC on the later part); magnitude (B) and level (A), OLS of the
champion residual on the standardised cell, or ridge at a fixed declared
penalty, scored by paired MAE skill; direction (C), a fixed logistic
regression on the champion score plus the cell, scored by Brier skill,
with log loss and calibration as secondaries; quantiles (E), fixed
linear quantile regression per declared level, scored by pinball
skill; distribution (E), one predeclared probabilistic estimator (a
Gaussian location-scale regression where defensible, else the
parametric head the page names), scored by CRPS skill; trajectory (D),
one fixed multi-output one-feature estimator scored by the aggregate
declared at stage 1 (the mean of per-horizon skill, or declared
weights). A fixed OLS screen evaluated out of sample on MAE is
permissible. Least-absolute-deviation regression would align the fitting
objective more directly with MAE. Whichever fit is declared is the one
the null replays. The distributional family never varies by cell. The rough
bars in SKILL.md conventions take the standardised effect; the paired
block bootstrap on identical anchors is the real uncertainty for every
metric.

Oriented primary skill. Every primary metric is carried downstream as a
skill statistic whose positive direction means improvement over the
champion, the one binding comparator: for a loss (MAE, Brier, pinball,
CRPS), L_champion minus L_model; for rank IC, model IC minus champion IC.
Positive beats the champion, zero ties, negative loses. The comparator is
a rule: the champion reselected at each refit from the stage 1 candidate
list. This one number is used at nomination, the judge read, live
evaluation and monitoring, so nothing downstream carries a
metric-specific sign convention or a second comparator; the raw metric is
reported beside it. Relative figures are reported under explicit names
such as relative_mae or brier_skill_score and never set a bar.
Constant-forecast rank IC: not applicable. Evaluate the constant baseline
using applicable loss metrics. A zero may stand for it only as a declared
reporting convention, never presented as a computed correlation; under a
rank IC primary metric a constant cannot be ranked, so it is never the
champion unless that convention was declared before any outcome was read.
Oriented skill is the forecast performance of a complete model against
the champion (stages 7 to 10) and a different object from the stage 5
screening statistic: for the timing screen, the rank IC of a cell against
the champion residual is not model IC minus champion IC.

## Champion fit for the null

Declared at stage 1, fitted point-in-time at every refit, and matched to
the target family; the null adapter below must match it.

| Target family | Champion fit used by the null |
|---|---|
| Level, point change (A, B) | OLS or fixed ridge, declared ex ante |
| Direction (C) | logistic, or the declared probability model |
| Quantiles (E) | the declared quantile-regression champion |
| Distribution (E) | the declared probabilistic champion |
| Trajectory (D) | the declared multi-output champion |
| Bounded continuous | the declared support-respecting model or link |

## Null adapter per family

The null removes incremental information and keeps the champion's
conditional structure, the target's valid support, the clock and the
declared regime structure. Continuous level and change targets (A, B,
and D per horizon): the champion's point-in-time forecast plus the
out-of-fold champion residual, resampled by the SKILL.md null-method
rule (shift or stationary block bootstrap when the scale is stable,
standardise-and-rescale or within-regime resampling when not).
Direction (C, binary target): the residual lives on the probability
scale, and an ordinary continuous PIT is not uniform for a Bernoulli
outcome, so the residual is the randomized discrete PIT (the
distributional transform) under the champion probability, resampled
with the declared clock-preserving dependence method and inverted back
to valid 0/1 outcomes; alternatively, outcomes are simulated as
conditional Bernoulli draws from the champion probability with the
declared dependence structure. An additive residual on a probability is
never used: it leaves the unit interval and stops being binary.
Distributional targets (E, a full predictive CDF): PIT residuals directly
under the champion CDF, resampled on that scale and inverted through it,
which keeps support, heteroskedasticity and the champion's conditional
shape. Quantile-only targets (a finite set of levels): a PIT exists only
through a full CDF, so the plan declares before the first screen a
monotone CDF reconstruction from the predicted quantiles, with its tail
rule and its correction of quantile crossing; the reconstructed CDF gives
the PIT residuals and the inversion. Without a defensible reconstruction
the page declares a quantile-specific support-preserving null instead.
Bounded
continuous targets (`physical-diff-addendum.md`): residuals on a
transformed scale (a link that maps the support to the real line),
resampled and mapped back, never additive on the bounded scale. The
adapter is named on the null page beside the method, and every replay
reruns the same point-in-time procedure.

## Calibration: declared at stage 6, diagnosed at stage 9

- Reliability diagram: ten equal-count bins on the nomination folds, and once
  on the judge years. The bins are a picture: no single bin gives a verdict.
  An overall verdict needs a declared test with its null and construction
  written down; without one, the page gives none.
- Brier beside the base-rate Brier (a reference); decompose into
  reliability, resolution and uncertainty when the sample allows.
- Calibrator, declared at stage 6: none, Platt (a logistic on the score) or
  isotonic. None is admissible when the model already outputs a
  probability. A calibrator is fitted on held-out inner predictions at each
  refit, never on the classifier's own training predictions, and belongs to
  the cell in the grid, the null, the judge read and live. A raw classifier
  score is never reported as a probability.
- Quantile coverage: the empirical coverage of each level with its paired
  interval. A 90% interval that covers 70% is a finding, said first.
- Conformal intervals: a time-series calibration scheme declared for the
  target's dependence and drift (rolling, adaptive, block, weighted or
  regime-conditional conformal); any separation between fit and calibration
  rows is justified by the mechanism it prevents, as the leakage rule says,
  and a fixed gap is never treated as restoring exchangeability by itself.
  Coverage is reported overall, per declared regime and on the judge years.
- The ledger scores matured outcomes with the same metrics.

## Domain baselines

General: no change, always one side, trailing base rate, trailing mean,
seasonal naive where a season exists. Level targets add AR(1) and exponential
smoothing. Physical differentials add the netback and delivered-parity
baselines in `physical-diff-addendum.md`, reported beside the constant ones.
