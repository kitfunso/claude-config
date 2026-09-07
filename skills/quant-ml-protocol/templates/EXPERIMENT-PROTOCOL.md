# EXPERIMENT PROTOCOL — <project> (v1, <date>)

> Instantiated from the quant-ml-protocol skill. This file governs every run.
> Amendments are appended with a version bump and a date — never edited in
> place. An experiment not declared here (or in a hashed registry it points
> to) is a diagnostic, not evidence.

## 0. Sample-size math (fill in FIRST)

- Anchors: <n>  ·  horizon overlap: <h>  ·  **n_independent ≈ <n/h>**
- SE(rank IC) ≈ 1/sqrt(n_indep) = **<value>**
- Detectable-effect floor (2×SE): **<value>** — any smaller 'finding' is
  noise-sized and must be labeled so.
- Feature cap (~n_indep/8): **<k>**

## 1. Instrument & target

- Instrument, tenor, and measured holdability: <...>
- Target: <horizon> move MINUS <carry/roll/basis — everything the market
  pays for free>, constructed roll-clean; never normalized: <yes/no + why>
- Naive-baseline check: always-long / always-short / RW / carry-sign scores
  on the raw target: <...> (if a one-side strategy scores well, fix the
  target before modeling)

## 2. Data register

| source | vintaged? | revision risk | staleness cap | PIT rule |
|---|---|---|---|---|
| <...> | <yes / stored-revised / unknown> | <...> | <...> | <available_ts rule> |

Stored-revised sources: vintage snapshots start <date>; lag-stress results:
<...>

## 3. The decision rule (attackable at every gate)

- Primary metrics (≥2): <ranking metric> AND <money metric, costs = <...>>
- Tie-break: parsimony
- Nulls are: <vetoes | caution flags> — flags ride every future report
- Multiplicity: N × α line on every pass; joint bootstrap (SPA | StepM)
  when lanes share data: <yes | N/A, why>
- Promotion requires: the Stage-6 user gate, explicitly signed off

## 4. Declared experiments (registry)

| id | declared (date, hash) | design | null design | status | verdict |
|---|---|---|---|---|---|
| <...> | | | | DECLARED / RUNNING / DONE | |

## 5. NOT-DONE table (mandatory in every report)

Pre-seeded with the Stage 4.1 mechanism ladder. A rung leaves this table
only when its registry row (section 4) carries a verdict.

| declared item | status | why / slot |
|---|---|---|
| 4.1.1 level models (AR / ARIMA / ETS / HAR) | NOT RUN | <...> |
| 4.1.2 magnitude + distributional lane (pinball / CRPS) | NOT RUN | <...> |
| 4.1.3 rolling-length sweep + recency weights | NOT RUN | <...> |
| 4.1.4 lag structure of outside data | NOT RUN | <...> |
| 4.1.5 feature selection with error control (knockoffs) | NOT RUN | <...> |
| 4.1.6 monotone constraints / partial pooling | NOT RUN | <...> |
| 4.1.7 Optuna/TPE + zero-search champion | NOT RUN | <...> |
| 4.1.8 ensembles across families | NOT RUN | <...> |
| 4.1.9 late-lane data in every window config | NOT RUN | <...> |
| 4.1.10 execution lag + real costs inside the metric | NOT RUN | <...> |
| <...> | NOT RUN | <...> |

## 6. Accrual list (thin candidates — scheduled, never forgotten)

| candidate | n when tested | flag | re-test due |
|---|---|---|---|
| <...> | | | |

## 7. Caution flags in force

| flag | source | first declared | rides until |
|---|---|---|---|
| <...> | | | |

## 8. Prospective ledger contract

- Schedule: <when the model runs, and what price the entry is>
- Ledger: append-only, one row per scheduled anchor, spec-tagged, judged on
  its own date, never edited; prior-spec rows archived and labeled.
- Tripwires: REVIEW <value> · KILL <value> · operational kill <skip/error
  rate>; judged by <e-process | confidence sequence>, valid under daily peeks
- Sizing: raw <scalar> · shrunk for estimation error <scalar, SE used>
- Drift monitor: <rolling window vs backtest distribution, alert threshold>

## Amendment log

- v1 <date>: instantiated.
