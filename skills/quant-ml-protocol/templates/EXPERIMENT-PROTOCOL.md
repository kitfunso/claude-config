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
- Promotion requires: the Stage-6 user gate, explicitly signed off

## 4. Declared experiments (registry)

| id | declared (date, hash) | design | null design | status | verdict |
|---|---|---|---|---|---|
| <...> | | | | DECLARED / RUNNING / DONE | |

## 5. NOT-DONE table (mandatory in every report)

| declared item | status | why |
|---|---|---|
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
- Drift monitor: <rolling window vs backtest distribution, alert threshold>

## Amendment log

- v1 <date>: instantiated.
