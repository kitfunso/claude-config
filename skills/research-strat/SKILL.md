---
name: research-strat
description: Research a new trading-strategy idea across the full data-available universe (all instruments x 5m/15m/1h/4h) through the locked horizon + shuffled-null gates and the 8-test battery, dedup vs the live book, and produce a promotion scorecard. Pure research - never touches the locked 21-strategy live book.
---

# research-strat

Turn a plain-English strategy idea into a graded candidate using the SAME pipeline that
built the deployed 21-strategy book. Search everything, then filter. Output is a
scorecard for a human promotion decision - this skill changes nothing that trades.

## Firebreak (NEVER violate)
- NEVER edit `data/tournament/final_universe.json` or `deploy_book.json` (the live book).
- NEVER edit `engine/families.py` (the live registry). New ideas go in `engine/families_candidates.py`.
- All output stays under `data/tournament/candidates/<date>/` (the driver asserts this).
- Promotion into the live book is a HUMAN edit of `final_universe.json` at a re-lock point,
  never automatic. Present the scorecard and STOP.

## Steps
1. **Translate** the idea into a CAUSAL `make_signal(bars, params) -> pd.Series in [-1, 1]`
   plus a 4-cell `param_grid`. Causality rule: bar `t` may use only data up to and
   including `t`; any rolling statistic used as a threshold must be `.shift()`ed so the
   current bar is excluded from its own gate. Add a `FamilySpec` and register it in
   `CANDIDATES` in `engine/families_candidates.py`.
2. **Sweep**:
   ```
   python scripts/research_strat.py --family <name>
   ```
   Defaults to every data-available instrument x {5m,15m,1h,4h}. Use `--symbols` /
   `--freqs` to scope, `--null-trials N` to trade speed for null precision.
3. **Read** `data/tournament/candidates/<date>/<name>.html`. Report which `(instrument,
   freq)` cells clear the deploy bar and their correlation vs the live book.
4. **STOP.** Present the scorecard. Do not promote, do not touch the live book.

## The gates (locked - docs/CONSTRUCTION_SPEC.md + RESEARCH_PLAN.md s4)
- **Causality preflight**: prefix-stability probe before the sweep. A candidate whose signal peeks
  at future bars (shift(-1), centered window, full-sample normalization) is REJECTED outright. CI
  (`tests/test_causality.py`) covers candidates too.
- **Pass A horizon**: OOS Sharpe > 0.3, gross > 0, grid-stability >= 70%, cost-share < 60%, maxDD > -25%.
- **Pass B shuffled-null**: real Sharpe beats >= 90% of signal-permuted nulls (`null_pass_rate <= 0.10`).
- **8-test battery** (run on the MEDIAN grid cell, not the best - avoids hindsight selection):
  T1 CPCV/PBO, T2 regime, T3 grid+sensitivity-regrid, T4/T5 feature+ablation (ML only - **fail-closed**
  if uncomputable; N/A=pass for rules), T6 annual, T7 decay, T8 trade-efficiency.
- **Deploy bar**: must-pass(T1, T7) AND fail at most ONE *applicable* test (rules 5/6, ML 7/8)
  AND walk-forward Sharpe >= 1.0.
- **ADD-READY** (the headline verdict): deploy-bar pass AND corr < 0.75 vs every LIVE strat
  (`final_universe.json` allowlist, not all of combined_daily) AND measured cost available. A cell
  that passes the bar but is redundant or cost-unverified shows `PASS (...)`, not ADD-READY.

## Notes / known limitations
- **Causality is your job in `make_signal`.** The preflight + CI catch obvious leaks, but write
  causal signals: any rolling stat used as a threshold must `.shift()` so bar t is excluded from
  its own gate.
- **ML candidate contract**: an ML family (name in the ridge/logreg set, or grid carrying
  `alpha`/`registry_names`/`C`/`l1_ratio`) must expose the `registry_names` feature list so T4/T5
  (feature perturbation + ablation) can run. If they cannot be computed, the cell FAILS the bar.
- Cost: missing measured L2 cost falls back to 1x spread (optimistic) and marks the cell
  `cost-unverified` -> not ADD-READY. Run the cost calibration to clear it.
- `--resume` skips cells already in today's JSON (the run persists after every battery cell).
- The shuffled-null in `engine/walkforward.py` is a full i.i.d. signal permutation (relatively
  lenient). A stricter block/circular permutation belongs in that LOCKED path - do not change it
  without a re-lock.
- Families needing auxiliary joins (lead_lag, funding_fade, coinbase_premium) need their data
  wired before they produce cells; without it those cells skip (recorded in the error list, not
  silently dropped).
