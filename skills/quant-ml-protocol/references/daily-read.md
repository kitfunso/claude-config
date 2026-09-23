# The daily read

Read at stage 10. The last stage of research, never shipping. Everything
below is declared on the plan page before the first ledger row.

## Start condition

The daily read starts only if the standing family beat the champion on the
judge read (paired interval clear of zero). Otherwise either the champion
alone runs, so the ledger accrues outcomes for it, or nothing runs; the page
says which and why.

## The live spec

The frozen cell from stage 8: family, shortlist rule, cap, hyperparameters or
the declared search with its retuning schedule, calibrator, window and refit
cadence. It is rolled forward through the same code path. At each declared
refit date, train on the eligible rows within the selected window. Between
refits, reuse the last fitted model. Studies rerun only on the declared
retuning schedule; between retuning dates the last study's hyperparameters
are reused.

Three ids:

- spec_id: frozen modelling and decision rules. Hashed from the cell id,
  the code commit and the environment; the dataset manifest is left out.
- fit_id: a particular scheduled refit, including its training-data
  snapshot. The manifest's state at that fit is hashed here.
- forecast_id: a particular prediction and input snapshot, carrying the
  input snapshot hash and the cutoff time. A data pull between refits
  changes the forecast's input snapshot, not the fit: it makes new
  forecast_ids, each hashing its new input snapshot, under the current
  fit_id, never a new fit_id or spec_id.

All three are required, and a correction to an id scheme names all
three: without fit_id a refit cannot be audited, and without forecast_id
a ledger row cannot be tied to the inputs it saw. Only a spec_id change
opens a new ledger track. Routine refitting under the
same frozen rules should produce a new fit_id, and a data pull only new
forecast_ids, not erase the continuity of evidence for spec_id.

## The run

1. Scheduled ingest.
2. Validate incoming rows with the stage 2 checks.
3. Point-in-time features through the research code path.
4. Load the spec by spec_id and the current fit by fit_id.
5. Forecast, with probability or quantiles when declared.
6. Apply the decision rules from the trading page, if there is one.
7. Write the forecast row and its metadata.
8. Publish and alert.

A failed validation or availability check at step 2 or 3 skips the row and
logs why. It never carries a stale forecast forward.

## Training-serving consistency

One code path builds research features and live features. On the first live
run and monthly after: truncate the raw data at a past anchor, regenerate,
compare to the full-history features and to the research prediction at that
anchor; equal to tolerance or the run is blocked. This is the stage 4
future-mutation test pointed at production.

## The ledger

Append-only. Forecast row: forecast_id, spec_id, fit_id, run time, cutoff
time, input snapshot hash, anchor date, horizon, point forecast, probability
or quantiles when declared, the decision when there is one, and the
champion's forecast with its fit_id, so the live comparison can be audited.
Outcome record, appended when the target matures: forecast_id, matured
value, matured time, the score under each declared metric. Nothing is edited; an off-grid or odd
row gets a label and an explanation. Old-spec rows are labelled, never
deleted: deleting one row makes every remaining row worthless.

## The read rule, declared before the first row

- Statistic: the stage 1 primary metric on matured outcomes as oriented
  primary skill against the champion, the frozen comparator rule (for a
  loss, the champion's loss minus the model's on the same rows; for the
  timing read, model rank IC minus champion rank IC), with the raw metric
  and sign hit beside it. The reference baselines, the base rate among
  them, are reported and never set the bar.
- Minimum matured outcomes before the first claim: ((z_level + z_power) /
  e)^2, at least 30, at the declared interval level and power (two-sided
  95% and 80% by default, so z_level = 1.96 and z_power = 0.84), where e
  is the stage 1 smallest effect worth having in the primary metric,
  standardised as the conventions say: a rank IC as itself, counted in
  independent outcomes (matured rows divided by horizon overlap); a
  paired-loss metric as the smallest useful mean improvement over the
  long-run standard deviation of the per-anchor paired differences on
  nomination rows (block bootstrap or HAC, named on the page), counted in
  forecast anchors and not divided again by overlap. The count is a
  planning approximation, not a universal formula for rank-IC
  differences, whole-search maxima or sequential stopping; a rank IC
  count is rougher still, and a ledger read by a confidence sequence
  takes its count from the sequence's boundary. The page states the date
  the ledger reaches the count at its accrual rate; when that date lies beyond the declared usefulness
  horizon the ledger is kill-only: it can detect decay and cannot
  confirm skill, and the page says so before the first row. The judge
  read is shown beside the rule as context, never as its input.
- Schedule: one fixed read date written on the page, or a confidence
  sequence (an interval valid at every look; a mixture-sequential or
  running-intersection bound). With neither implemented, the fixed date is
  the rule. A daily glance is allowed; a claim, a spec change or a stop
  informed by the ledger before the rule holds is a second look.
- The claim: the ledger's binding statistic is the same oriented primary
  skill, against the champion under the same frozen rule, that nomination
  and the judge read used; the raw metric and the declared secondaries sit beside it,
  and no live claim changes metric, comparator or orientation. The ledger
  skill with its interval is read beside the judge skill; a ledger skill
  below the judge interval is decay, said first.

## Monitoring

Data quality: missingness, staleness against the cap, out-of-range values per
source. Feature drift: each shortlist feature's live value against its
nomination-year distribution, with the count outside the 1st to 99th
percentile. Prediction drift: the forecast distribution against the
backtest's. Accuracy: rolling oriented primary skill in the declared metric
on matured outcomes over a declared window (td3c uses 26 weeks), against the
champion as in the frozen spec, read against the backtest's own
distribution, alarm at its 5th percentile, with the target family's secondaries beside it
(timing: oriented rank IC skill with sign hit; magnitude: MAE skill with
rank IC and sign hit; direction: Brier skill with reliability and log loss
or balanced accuracy; quantile: pinball skill with coverage; distribution:
CRPS skill with central-interval coverage; trajectory: the aggregate horizon
skill with per-horizon diagnostics). Calibration: reliability on matured
outcomes.
Operations: failed, late and skipped runs. Every alarm is written on the
page and reviewed; nothing refits automatically on an alarm.

Monitoring actions. Operational and data-validity alarms (a missing input
or one stale past its cap, an availability or schema failure, out-of-range
values, a failed feature-generation or training-serving check, a broken
feed) may skip the row, pause the lane or invoke the predeclared fallback
at once, because they select on nothing realised. Performance alarms on
matured outcomes (rolling primary skill, rolling Brier, MAE skill or IC,
live degradation) trigger review and diagnosis only: they cannot alter,
stop or replace the standing spec before the ledger read rule permits a
claim, unless a separately predeclared anytime-valid kill procedure
governs them (an e-process or a confidence sequence, as the trading
layer's tripwires use). A fixed-window threshold inspected repeatedly is
not permission to stop early.

## Retrain, challenger, fallback

Retrain schedule = the cell's refit cadence and its declared retuning
schedule, no more often. A challenger runs beside the incumbent on the
ledger under its own spec_id and replaces it only under the same read rule
on the same matured outcomes; a spec corrected after a verified validity
failure (SKILL.md, hard validity rules) runs the same way. Fallback spec: the
champion alone, or no change. The triggers that switch to it are declared
before the first row and the switch is a labelled ledger event: an
operational or data-validity alarm with its predeclared trigger (a failed
availability check, a data-gap tripwire) switches immediately; a
performance alarm switches early only through a separately predeclared
anytime-valid kill rule, and otherwise waits for the binding ledger read.

A judge-derived idea (a feature dropped, a gate added, a cadence
changed because of what the judge years showed) enters only as a
labelled challenger under this rule, never scored on the judge years that
suggested it; the standing spec is never edited from the judge read.
