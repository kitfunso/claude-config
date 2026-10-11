# Audit: the heavy checks

For a claim that will move real money or go out as a public result, after stage 5
and before any sizing. Each check is priced in compute hours on the campaign page
before it runs. None of them is a research stage, and none replaces the evaluator.

The full text of the 2026-10-03 protocol these checks come from stays in git:
- `git -C ~/.claude show 6dac91a:skills/quant-ml-protocol/SKILL.md`: Multiplicity,
  Null worlds and Power (lines 310-414), the screen (stage 5, lines 760-825), the
  gauntlet (Breadth 7, lines 180-189).
- `6dac91a:skills/quant-ml-protocol/references/targets-and-metrics.md` lines 117-163:
  the champion fit and the null adapter per target family (binary, quantile,
  distributional and bounded targets).
- `6dac91a:skills/quant-ml-protocol/scripts/coverage_check.py` and
  `templates/pipeline-plan.html`: the coverage table and the plan page.

## 1. Full-search null replay

The bar for a search is what the same search finds when the extra information is
removed and everything else kept. The null target is the champion's point-in-time
forecast plus its out-of-fold residual, resampled as one series by a method that
keeps the clock: a circular shift or a stationary block bootstrap when the
residual's scale is stable across the block, standardise-and-rescale or
within-regime resampling when it is not. A binary, bounded or distributional target
resamples on the probability or PIT scale and inverts back, so outcomes stay inside
the support. Each null world reruns the whole procedure point-in-time, every tuning
study included, and records the maximum over the search. p = (b + 1) / (B + 1),
where b counts worlds whose maximum beats the real statistic. B is at least 100;
below 100 the result is labelled coarse, and 20 is the floor. Cost: studies per
world x B x trials per study, stated before the run.

Questions that caught errors here:
- "Is the cutoff a number I chose, or the null's?" (bd-forecast 2026-08: an
  11,872-cell search found +0.099 while all 20 shift replays found more.)
- "Does the null keep the champion?" (td3c 2026-09-22: the question was what adds
  after a champion at rank IC 0.44, so the null became the champion fit plus the
  shifted residual.)
- "Does the null keep the clock?" (outside review 2026-09-22: a whole-block shift put
  crisis residuals into calm years.)
- "Are twenty shifts twenty draws?" (offsets closer than a horizon are near
  duplicates; space them at least two horizons apart.)
- "Can this test say yes?" (td3c planned 203,700 cells on about 100 independent
  observations; a bar above any plausible effect is theatre.)

## 2. Signal-injection power

Plant the smallest effect worth having in a real feature, replay the whole search,
and count the share of worlds where the planted feature clears the cutoff actually
used. 80% is the usual target. Below it, the page says the search was underpowered
for the effect that matters, whatever the data held.

## 3. The gauntlet

On the frozen spec, before sizing: G1 leave-one-year-out (does the sign hold
dropping any year); G2 neighbouring horizons (do adjacent horizons agree); G3
knockout per feature and per feature group; G4 lag stress on every B to D input by
its declared lag rule. Results sit beside the spec as flags.

## 4. Adversarial validation

A classifier that separates evaluator-window rows from final-read rows on the
features. A high AUC is expected for time blocks; the output is the list of
separating features, and each gets a knockout.

## 5. Trading P&L overfitting

Probability of backtest overfitting (`pypbo.pbo`) on the T x N matrix of every
logged configuration's returns, and deflated Sharpe (`pypbo.dsr`) with N equal to
the ledger's row count. `pypbo` warns that PBO suits weakly autocorrelated returns;
say so beside the number when the returns are not.

## Reporting an audit

The method, B, what the null preserves, the cutoff with its uncertainty, the
p-value labelled coarse below 100 worlds, and the compute it cost. A failed audit
blocks the money decision it was run for; the research result stands as reported.
