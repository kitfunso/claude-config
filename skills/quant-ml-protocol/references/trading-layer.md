# The trading layer

Its own page after stage 10, when a project trades the forecast. Money never
enters the research metric: research answers whether the forecast has skill,
this page answers whether it pays. Every rule here was paid for in
bd-forecast (2026-08), AF2 (2026) or the grade-differentials kickoff
(2026-09-03).

## Expression and holdability

Name the instrument that carries the trade and measure, never assume, that it
lives through the horizon: a front contract that expires mid-horizon cannot
carry it (bd: the second month was the shortest holdable tenor for a
seven-week horizon). Physical differentials trade through the window
bid/offer, a CFD plus cargo, an arb-engine route or a term-lifting
nomination; name which.

## Costs, inside the money metric from the first backtest

Bid-offer, commission, financing times calendar days held, borrow, roll
cost. Physical: demurrage, freight adjustment, quality escalators, the
bid-offer in the window. Execution lag: the entry is the first tradable print
after the signal is computable, never the assessment the signal was computed
from; measure the lag. A money number dealt at the mid is a diagnostic (AF2:
+3.93 bps per day gross became about +1.13 once the stated financing was
applied).

## Decision rule

Declared on the nomination years: a threshold on the forecast or the
probability; sizing (fixed, vol-target, or a Kelly fraction shrunk by the
edge's standard error, Baker and McHale 2013); risk limits; liquidity. For
the probabilistic read, expected utility over the declared distribution
rather than the most likely side. Overlapping signals: say whether a new
signal adds to, replaces or adjusts the position; P&L is measured at the
portfolio level; overlapping horizon returns are never counted as separate
fully invested trades.

## Economic nomination and judge

The skeleton (instrument, execution time and lag, cost categories,
holding rule, overlap treatment, risk limits, primary economic metric)
is declared and frozen at stage 1. The decision rule (threshold,
sizing, holding) is selected on the nomination years against that
skeleton; one economic rule is frozen before stage 8 opens, before any
forecast or economic judge outcome is inspected; it gets one economic
judge read on the judge years, listed in the judge-exposure box beside
the forecast judge read; the trading ledger follows. A threshold,
holding rule or instrument revised after the forecast judge read, or
chosen on judge-year P&L, is a second selection, and the page says so.

## Backtest engine

Timestamp-correct signals; execution delay; tradable contract definitions and
rolls; the costs above; slippage; position limits; financing and margin;
daily mark-to-market with the mark's freeze time measured (bd: an intraday
pull carried a partial-day mark into the settle panel); portfolio exposure
and risk limits. Metrics: net P&L, Sharpe with autocorrelation-robust errors
(block bootstrap or Newey-West), drawdown, turnover, each with its paired
interval against no-trade and against the champion-rule strategy.

## Tripwires, declared before the first live row

A review threshold and a kill threshold from the backtest's own return
distribution; an operational kill on skip or error rate; a lane too thin to
confirm its edge at its accrual rate is kill-only, with the detectable-effect
horizon stated, taken from the ledger power rule at the declared level and
power (`daily-read.md`) or from the confidence sequence's boundary. The
ledger is peeked at every run, so fixed-n tests on it are
invalid: an e-process for the kill test and a confidence sequence for the
edge estimate keep the declared error rate at every stopping time. Physical:
a PRA methodology notice on the benchmark or the grade pauses the lane until
the regime register is updated; a missing benchmark or leg row skips the
row, never carries; entry marks are the next assessment, never our own
window activity.

## Sizing shrinks for estimation error

The edge that sets the size is an estimate from a thin ledger. Shrink the
size scalar by the edge's standard error and print the shrunk size beside the
raw one.
