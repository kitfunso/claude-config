# Data hygiene

Read at stage 2. Every check here is a test under `tests/`, run on the frozen
pull and again on every later pull before it enters a result.

## Quality checks, automated

Duplicate (timestamp, key) rows. Missing observations against the source's
own calendar. Units and currency per column, declared on the audit page and
asserted as a range. Spikes and erroneous zeros: a change beyond k sigma or a
zero on a positive series is flagged, never removed by the test. Unexpected
negatives. Provider outages: runs of missing rows. Stale prices: a value
repeated for n sessions on a series that moves daily. Contract
discontinuities: roll and expiry dates. Calendar and timezone: the timezone
of each table's observation date written down; sessions and calendar days
never mixed. Universe survivorship: entities, grades, routes, contracts or
series that left the universe, and whether today's pull still shows them; a
universe reconstructed from today's list is labelled so. Output: a hygiene
report page listing every flag and its disposition.

## Outliers

Identify, check the source, compare a related instrument, decide error or
event. Correct errors, keep events, and log every intervention (date, series,
old value, new value, reason) on the audit page. The target is never
winsorised or clipped: the extreme moves are what the model is for. A feature
may be rank- or z-transformed instead.

## Missing data, by mechanism first

| Situation | Treatment |
|---|---|
| Holiday, no session | Calendar-aware: the row does not exist on the master calendar |
| Not yet published | Latest known value, forward-filled up to the staleness cap; older is missing |
| Provider outage | Missingness indicator plus forward fill to the cap |
| Feature history starts late | The late-start rule at stage 5: window-matched null, flag, re-test date |
| Persistent gap | Investigate the source; exclude and list |

The staleness cap is a dated, source-specific convention on the plan page,
set by the source's expected publication cadence and market use, never a
fixed ratio to its nominal frequency. Imputation with
fitted parameters (median, model-based) is fitted inside the fold at each
refit. A missingness indicator is a cell like any other and counts in K.
Models that accept missing values still get the indicator.

## Point-in-time availability

PIT availability is a source property, not a universal entry requirement.
Exact historical vintages are used where they exist; where they do not, the
research may use the vendor's supplied history, and the limitation is
carried into every result that depends materially on that source. Every
source gets a row in the availability record, on the audit page:

| Field | Content |
|---|---|
| source | vendor or system |
| series | the column or table |
| pit_status | verified / unavailable / unknown (provenance grade A / B or C / D, SKILL.md stage 2) |
| revision_risk | low / medium / material / unknown |
| observation_date | the column that dates the observation |
| release_date_rule | how the available time is derived (release calendar, publish timestamp, observation date plus lag) |
| vintage_available | yes / no, and where the archive lives |
| correction_policy | how the vendor handles corrections and restatements |
| lag_sensitivity | the declared lag or revision sensitivity (+4 weeks by default for slow fundamentals, a lag ladder, snapshot, revision, none) |
| notes | what the grade rests on |

Known temporal leakage stays forbidden whatever the grade: no feature whose
known publication date is after the cutoff, no future observation shifted
backward, no transform fitted on future rows, no judge outcome inside an
earlier feature. A result that depends materially on a B to D source is
reported as a historical backtest on vendor-revised history, never as a
fully point-in-time backtest.

## Alignment

One master prediction calendar: the target's. Lower-frequency sources join
as-of by their available time and forward-fill to the cap. Higher-frequency
sources aggregate only the observations available before the cutoff.
Exchange holidays, contract rolls and sessions come from the source calendar,
never from an assumption that every day trades.

## The freeze manifest

Anchor cutoff. Raw pulls in dated immutable directories; a re-pull is a new
directory. SHA256 per file, appended, never rewritten. Code commit.
Environment lock hash. The schema manifest with exact counts. The hygiene
report. The data dictionary, which is the audit page's columns: name, source,
units, frequency, observation-date column, available-time rule, ingestion
time where it lags availability, provenance grade (A to D) with its
revision risk, missing
policy, first date, live feed (available in production, from where; a column
with no live feed is research-only and labelled so). If a result changes
later, the manifest says whether the data, the code or the environment moved.
