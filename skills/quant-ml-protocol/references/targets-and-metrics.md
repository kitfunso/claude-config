# Targets and metrics

Read when building the evaluator (the target and its metric), when a draft outputs a
probability or quantiles (the calibration choice), and at stage 5 (calibration
diagnostics). Every target declared here is scored on the same anchors and the same
evaluator windows as the point target.

## Target families

| | Target | When it fits |
|---|---|---|
| A | Level, S at t+h | The future level itself matters (storage, load). Carries the unit root; baselines add AR(1) and exponential smoothing on the level. |
| B | Change, S at t+h minus S at t; log change for a positive series | The default point target for a price, spread, rate or differential. |
| C | Direction, 1 if the change is positive | Declared beside B when the decision is a side. The trailing base rate is the reference, never 50%. |
| D | Trajectory, S at t+1 to t+h | Only when the path matters, not the endpoint. Multi-output. |
| E | Distribution of S at t+h given X at t: quantiles or a parametric head | Declared beside B when the decision needs a size, an interval or a tail. |

B is the default point target for a price, spread, rate or differential, a default
and not a universally better target; A stays available where the decision concerns
the future level, and the campaign page says which. C and E are declared beside B,
never instead of it, each with its own metric; nothing is chosen between them on the
final-read window. A directional read that beats its base rate while the point read
is flat is a finding to report, not a switch of target. A competition target is
whatever the organiser scores, on the organiser's metric.

Horizon strategy: direct, one model per horizon, by default. A joint-horizon or
recursive model is its own draft under the same keep rule; a recursive one accounts
for its accumulated forecast error and uses only information available recursively
at prediction time.

## The metric per target

| Target | Primary | Secondaries | Reference baselines (reported) |
|---|---|---|---|
| Point change, timing decision | rank IC | MAE, sign hit | no change and trailing mean, on MAE (a constant has no rank IC) |
| Point change, magnitude decision | MAE, with relative_mae (model MAE over no-change MAE on the same rows); Huber where the page says why | rank IC, sign hit | no change, trailing mean |
| Direction | Brier | log loss, balanced accuracy, reliability diagram | trailing base rate, majority side |
| Quantiles | pinball loss per level | coverage per level | the unconditional quantiles of the training rows |
| Distribution | CRPS | coverage of the central intervals | the unconditional distribution |
| Level | MAE, MASE (MAE scaled by the in-sample one-step naive MAE, Hyndman and Koehler 2006; a ratio to an out-of-sample same-horizon baseline is always called relative_mae) | RMSE | naive last value, AR(1) |

Brier, log loss, pinball and CRPS are proper scoring rules: a forecaster minimises
them by reporting what it believes. Accuracy and sign hit are not, so they stay
secondaries. Every comparison carries the paired block-bootstrap interval on
identical anchors; a Diebold-Mariano test on the same paired loss differences, with
autocorrelation-consistent errors, is the parametric equivalent and is reported
beside it when a reader expects one.

Predicted quantiles are non-crossing: the fit enforces monotone quantiles, or one
declared monotone rearrangement or isotonic correction is applied, fixed before the
first run.

## Oriented skill

The evaluator carries every primary metric as a skill whose positive direction means
improvement over the champion: for a loss (MAE, Brier, pinball, CRPS), the
champion's loss minus the model's; for rank IC, the model's IC minus the champion's.
Positive beats the champion, zero ties, negative loses. The same number is used in
the evaluator, at the final read, in the live ledger and in monitoring, so nothing
downstream carries a metric-specific sign or a second comparator; the raw metric is
reported beside it. Relative figures go by explicit names such as relative_mae or
brier_skill_score and never set a bar. A constant forecast has no rank IC: score it
on the loss metrics that apply, never as a computed zero correlation.

## Calibration

- Calibrator, declared with the draft that needs it: none, Platt (a logistic on the
  score) or isotonic. None is admissible when the model already outputs a
  probability. A calibrator is fitted on held-out inner predictions at each refit,
  never on the classifier's own training predictions, and belongs to the run, the
  final read and live. A raw classifier score is never reported as a probability.
- Reliability diagram: ten equal-count bins on the evaluator windows, and once on the
  final-read window. The bins are a picture; an overall verdict needs a declared
  test.
- Brier beside the base-rate Brier; decompose into reliability, resolution and
  uncertainty when the sample allows.
- Quantile coverage: the empirical coverage of each level with its paired interval.
  A 90% interval that covers 70% is a finding, said first.
- Conformal intervals: a time-series scheme declared for the target's dependence and
  drift (rolling, adaptive, block, weighted or regime-conditional). A fixed gap
  between fit and calibration rows never restores exchangeability by itself.
  Coverage is reported overall, per declared regime and on the final-read window.
- The ledger scores matured outcomes with the same metrics.

## Domain baselines

General: no change, always one side, trailing base rate, trailing mean, seasonal
naive where a season exists. Level targets add AR(1) and exponential smoothing.
Physical differentials add the netback and delivered-parity baselines in
`physical-diff-addendum.md`.
