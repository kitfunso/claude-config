---
name: model-improve
description: Full commodity model improvement workflow — from audit through exhaustive feature engineering, two-stage selection, Optuna optimization, multi-layer validation, data source verification, and production deployment. Use PROACTIVELY when the user asks to improve, rebuild, develop, upgrade, or remodel any commodity trading model. Also trigger when user mentions feature engineering, model performance, Sharpe improvement, or adding new features to a commodity model. Quantamental project ONLY — do not fire in other repos; for general time-series model rigor elsewhere use quant-ml-protocol.
---

# Commodity Model Improvement Workflow

Complete model development pipeline for the Quantamental commodity trading system. Produces production-ready logistic regression models on remodeled futures contracts with full validation. This is the Quantamental instantiation of the general `/quant-ml-protocol`; on any conflict of statistical principle, that protocol wins.

Phases 0-8. Execute in order. Do not skip phases. Phase 0 and its pre-registration block are mandatory for any model that has traded live.

## Before You Start

Read these files to understand the current state:
1. `production/{commodity}_production_std.py` — current model
2. `PRODUCTION_MANIFEST.json` — baseline metrics
3. `production/shared_constants.py` — lot sizes, TC, tickers
4. `production/data_loader.py` — available data sources and `PUBLICATION_LAGS`

Identify the commodity's economic identity before engineering features. Every commodity has a unique supply/demand structure:
- **Precious metals** (gold, silver, platinum): real rates, USD, safe haven, jewelry, industrial
- **Base metals** (copper, aluminium): China demand, industrial cycle, housing
- **Energy** (crude, natgas, heating oil): OPEC, storage, weather, refining margins
- **Agriculture** (corn, wheat, soybeans): weather, planting, stocks-to-use, ethanol
- **Softs** (coffee, sugar, cocoa): EM supply, weather, currency
- **Livestock** (hogs, cattle): herd cycle, feed costs, slaughter

---

## Phase 0: Loss Diagnosis + Pre-Registration (mandatory for live-traded models)

Added 2026-08-11 (Keith directive). Before any feature work:

1. **Diagnose the realized losses.** Decompose by year/quarter, side (long/short/flat), sizing (lots vs vol at entry), regime, and feature staleness at decision Fridays. The key axis is **expected vs realized**: reconstruct what the current model's backtest says the live weeks should have returned (same signals, `futures_pnl` convention) vs what was realized. Convergent = the design honestly lost (alpha problem - guides the rebuild). Divergent = implementation loss (stale data, roll drift, unit bugs) - fix the pipeline, not the model. **STOP after the diagnosis report for review before Phase 1.**
2. **Pre-register the round.** Before touching data, write down: the hypothesis this round tests, the promotion bar, and the holdout window (item 3). Default promotion bar (Keith 2026-08-11): `compare_models` ACCEPT (>= +0.10 min Sharpe vs baseline) AND 8/8 battery AND **candidate min Sharpe >= 1.0** ("we need at least 1 sharpe"). Multi-round lanes get one written hypothesis per round, recorded before the round starts - this is what keeps a rounds-long search from becoming bar-shopping.
3. **Reserve a holdout NOTHING may touch:** the final ~18 months of data. It is run ONCE, on the final candidate only, after Phase 6 passes, and reported verbatim. Iterating against it even once un-blinds it for this lane.
4. **Anti-snooping scope:** the diagnosis may only name MECHANISM CLASSES, never date-specific patches. Any feature it motivates still needs independent economic rationale plus the full battery.

---

## Phase 1: Audit Current Model

```bash
python production/{commodity}_production_std.py
python scripts/preflight.py {commodity}
```

Document: current features, performance (CV/OOS/min Sharpe), coverage gaps, data sources.

---

## Phase 2: Data Source Audit

**Non-negotiable.** Every feature must use live, verified, publication-lag-aware data. The bar is reliability, not a source whitelist.

### The feature universe is INCLUSIVE, not EXCLUSIVE

**The full candidate pool = every source in `production/data_loader.py::PUBLICATION_LAGS` plus every column in the parquet caches under `data/cache/`.** That includes ~1,200 columns across 18+ sources: yfinance, FRED, COT, BIS, IMF, World Bank, USDA, NOAA, Open Meteo, ETF Flows, CPB Trade, DBnomics, export_sales, crop_progress, CONAB, FAO, FAS_PSD, China/India/Brazil macro, AEMO, GIE AGSI, shipping, Google Trends, ECB, and more.

The "Approved sources" table below is a **reliability floor** — these sources are ALWAYS candidates. It is NOT a ceiling or a whitelist. Do not read it as "only use these." Do not pass it to sub-agents as an exclusive list.

### Reliability floor — always in the candidate pool

| Source | Lag | Notes |
|--------|:---:|-------|
| yfinance | 0w | Real-time market data, auto-refreshed Fridays |
| FRED | 0w | Daily/weekly Federal Reserve data |
| COT/CFTC | 0w | Friday 3:30 PM ET release. Pipeline runs 6 PM ET, so lag=0 correct |

### Also always in the candidate pool — publication-lag managed via `align_with_lag()`

| Source | Lag | When useful |
|--------|:---:|---------|
| BIS | 0w | Credit spreads, exchange rates, debt service |
| ETF flows | 0w | Share count / AUM changes on commodity-backed ETFs (GLD, SLV, PALL, PPLT, USO, UNG) — direct investor-demand signal |
| EIA | 0w | Energy storage/production |
| Open Meteo | 0w | Weather at ag regions |
| NOAA | 0w | US weather / HDD / CDD |
| ECB | 0w | Euro-area rates |
| Crop Progress / CONAB | 1w | US and Brazilian crop state |
| export_sales | 1w | USDA export sales |
| USDA | 4w | Crop reports, hogs, cattle, FAS_PSD |
| World Bank Pink Sheet | 6w | Slow-moving features (annual cycles) |
| IMF / FAO / DBnomics | 8w | Broad commodity indices |
| CPB Trade | 10w | World trade monitor |
| China / India / Brazil macro | 8-12w | Country-specific sources via DBnomics / Argentina_ag |

### The ONLY excluded source

| Source | Why excluded |
|--------|-------|
| IndexMundi | Web scrape, no API, frequently months stale, breaks silently. Everything else is fine. |

### Verification rule (this is the actual non-negotiable)

For every feature that makes the final cut:
1. Last data date is within the source's declared `PUBLICATION_LAGS` tolerance (e.g., yfinance/FRED/COT < 4w; IMF < 8w; CPB < 10w).
2. Publication lag is applied via `align_with_lag()` — never a raw `.reindex(method='ffill')`.
3. Source is actively refreshing in `production/daily_cache_refresh.py` (not frozen).

If any of those fail, drop the feature.

### FRED honesty (measured 2026-08-10, ALFRED campaign)

FRED serves revised history, and the cache indexes monthly macro by observation date (a measured 46-85 day publication lead). **KEITH RULING 2026-08-11, NON-NEGOTIABLE: all backtesting uses ALFRED point-in-time data for revision-prone series.** The six covered series (`m2_money`, `industrial_prod`, `pce`, `china_cli`, `usd_broad`, `usd_em`) MUST be consumed through the PIT snapshot path (`production/pit_features.py::pit_feature`) in every backtest and remodel - never the raw fred cache. A candidate whose backtest reads a covered series off the legacy path is invalid regardless of its numbers. Series outside the covered set that turn out revision-prone get added to the ALFRED store first, then used. Daily market FRED series (rates, breakevens, spreads, FX, VIX) are never revised and stay fair game at lag 0.

Also run the freshness screen HERE, at candidate-construction time, not only in Phase 7: retired/frozen parquets (see `production/data_contracts.py`) must never enter the candidate pool.

### COT timing

Test lag sensitivity (0w vs 1w). If min Sharpe drops >50% with 1-week lag, document the timing risk.

### When briefing sub-agents (quant-analyst, etc.)

Do NOT write "approved sources only" or "yfinance / FRED / COT only" in briefs. That suppresses legitimate signal. Instead write: "feature universe = every source in `data_loader.py::PUBLICATION_LAGS` plus `data/cache/` parquets, with lag-aware alignment via `align_with_lag()`. Only IndexMundi is excluded." Explicitly name the additional categories relevant to the commodity (ETF flows, auto sales, China data, etc.) so the agent doesn't self-restrict.

---

## Phase 3: Exhaustive Feature Engineering

Build ~200+ candidates from ALL approved sources. Use `pd.concat(dict, axis=1)` to avoid DataFrame fragmentation.

### Data loading

```python
yf = load_yfinance()
fr = load_fred()
ct = load_cot()
commodity_price = yf[commodity].dropna()
idx = commodity_price.index
# Align all series with proper lags via align_with_lag()
```

### Feature categories (cover ALL of these)

1. **Own transforms**: momentum (4/8/13/26w), z-score (26/52), risk-adjusted mom, acceleration, percentile rank
2. **Related commodities**: ratios z-scored, cross-commodity momentum
3. **COT positioning**: MM/PM z-scores, binary extremes, spec concentration (MM/OI), cross-commodity divergence (e.g., z(silver_mm) - z(copper_mm)), COT breadth
4. **Energy/industrial**: crack spreads (HO/crude, gas/crude), sector ETFs (XLE, XLI, XLB), solar (TAN)
5. **Macro/rates**: TIPS (level, diff, z, binary), yield curve (inverted, steepening, acceleration), breakevens, Fed funds (continuous diff + binary), CPI
6. **Risk/credit**: VIX (z26/z52, high/low, acceleration), HY/IG/BBB/TED spreads, MOVE, GVZ, OVX
7. **FX/USD**: DXY (z, momentum, acceleration), USD broad, USD/EM, EUR/USD, USD/JPY, AUD/USD
8. **Liquidity**: M2 growth (13w/26w), Fed balance sheet growth
9. **Equity**: SPY/QQQ/IWM momentum and z-scores
10. **Multi-timeframe composites**: trend strength count, macro tailwind count, industrial health count, metals breadth
11. **Seasonal**: commodity-specific demand/supply seasons
12. **Binary regime indicators**: real_rate_easing, inflation_elevated, m2_growing
13. **Interactions** (4 categories — the creative edge):
    - Curve x macro regime (e.g., YC inverted x BEI rising)
    - Crack spread x inventory/flow (e.g., HO crack high x OI rising)
    - Risk x growth/demand (e.g., VIX elevated x copper recovering)
    - Supply stress x USD/liquidity (e.g., producers covering x DXY weak)

---

## Phase 4: Two-Stage Feature Selection

### Stage 1: IC Screen
- Spearman IC with remodeled futures labels
- Require: |IC| >= 0.015, p < 0.15, sign stable (same sign in first/second half of sample)
- Take top 60 by |IC|
- Honesty note (2026-08-11): this screen is a cheap pre-filter, not evidence. With ~800 weekly obs, 200 candidates at p < 0.15 yields ~30 false positives by chance, and the half-sample sign check reuses the selection sample. The shuffled-null gate (Phase 6) and the untouched holdout (Phase 0) are what actually price the search width.

### Stage 2: Greedy Forward Selection
- Walk-forward on remodeled futures contract using `build_futures_model_target()` + `compute_futures_pnl()`
- Add one feature at a time, keep only if `min(CV_Sharpe, OOS_Sharpe)` improves by >= 0.005
- Stop at max 15 features
- Use `fillna(0)` for features with shorter history
- **The OOS leg of `min(CV, OOS)` is consumed by this search.** After selection plus Optuna it is a second training set, not validation - only the Phase 0 holdout and the Phase 6 null gate remain honest. Log every configuration tried (features, params, score) to `data/registry/experiments.parquet` so search width is accountable across rounds.

---

## Phase 5: Optuna Optimization (300 trials)

```python
# Search space
C: log_uniform(0.05, 3.0)
train_weeks: int(40, 130, step=13)
retrain_weeks: int(4, 30)
long_threshold: uniform(0.51, 0.60)
short_threshold: uniform(0.35, 0.49)
# + 4 binary short rule inclusion + conditional thresholds

# Objective: maximize min(CV_Sharpe, OOS_Sharpe)
```

**After Optuna:** Compare best trial against default parameter grid. If greedy selection defaults scored higher, discard Optuna params. Prefer round numbers (C=0.20 not C=0.2137). The parameter grid is the robustness proof, not Optuna's single best trial.

---

## Phase 6: Validation Suite (ALL must pass)

**The battery source of truth is `research/full_sensitivity_validation.py` - all EIGHT tests (T1-T8).** Do not validate against a restated subset; the repo's suite wins where this table drifts.

| Test | Criterion |
|------|-----------|
| **T1 CPCV/PBO** | median Sharpe > 0, PBO < 0.30, positive paths > 60% |
| **T2 Regime** | >= 3/4 positive (high_vol, low_vol, trend_up, trend_down); each regime cell needs a minimum sample (>= ~40 weeks) or it reports N/A, never a free pass |
| **T3 Model param grid** | 125 combos (C x train x retrain): >90% positive |
| **T4 Feature param grid** | Sweep each feature's lookback/threshold: no cliff edges, 100% positive in cross-grid |
| **T5 Ablation** | Every feature contributes (removing it degrades Sharpe) |
| **T6 Annual** | >80% of years profitable |
| **T7 Signal decay** | <50% Sharpe decay at entry_delay=2 vs baseline |
| **T8 Trade efficiency** | >50bps net PnL per dollar traded |
| **COT lag** | Document sensitivity to 1-week lag |
| **Threshold sweep** (2026-08-11) | long/short thresholds +/- 0.02 grid: no cliff edges (they are optimized in Phase 5, so they need their own robustness proof) |
| **TC stress** (2026-08-11) | metrics survive 2x `TC_PER_CONTRACT` (efficiency at assumed TC is not robustness to TC being wrong) |
| **Shuffled-null gate** (2026-08-11) - BLOCKING, run it FIRST | Re-run the ENTIRE pipeline (IC screen + greedy + param grid) on >= 100 shuffled-label draws; compare the **GAIN over baseline**, not the level (shuffling kills the frozen core too, so levels are not comparable). The real gain must exceed the null p95. **MEASURED 2026-08-11 (crude round 7, 200 draws): IC-screen + greedy-on-min(CV,OOS) over ~120 candidates manufactures a MEDIAN +0.41 min Sharpe from pure noise.** A greedy gain of +0.35 scored p=0.58 - worse than a coin flip. Greedy consumes the OOS leg at every step, so any candidate selected this way without this gate has NO evidence of being real, however good its battery looks. Run this gate before spending the battery, compare_models, or the holdout on a candidate |
| **Holdout - run ONCE** (2026-08-11) | the Phase 0 pre-registered window, final candidate only, one run, reported verbatim whatever it says |

---

## Phase 7: Final Data Source Verification

After all validation, audit EVERY selected feature one more time:
1. Source is live and updating (< 4 weeks stale)
2. Publication lag correctly set in `PUBLICATION_LAGS`
3. Data available at pipeline time (Friday 6 PM ET)

If any feature fails: DROP IT, re-run Phases 4-6. (This should be a no-op: the same checks run at Phase 2-3 candidate construction. A failure here means the front screen was skipped.)

---

## Phase 8: Production Script

Follow `gold_production_std.py` pattern with futures adapter:

```python
from futures_model_adapter import (
    build_futures_model_target, build_futures_pnl_config, build_futures_results_frame)
from futures_pnl import compute_futures_pnl
```

Structure: `load_data()` → `build_features()` → `run_backtest()` → `get_live_signal()` → `main()`

Pre-commit:
```bash
python scripts/validate_outputs.py {commodity}
python scripts/preflight.py {commodity}
```

Promotion (2026-08-11 - replaces the old off-cycle deploy block):
```bash
python scripts/promote_model.py --baseline production/{commodity}_production_std.py \
    --candidate research/{commodity}_vN.py --version V<N> --notes "<description>"
python scripts/preflight.py {commodity}
```

**The Friday pipeline deploys.** Never write production outputs off-cycle by hand: `ALLOW_OFF_CYCLE_SCHEDULED_WRITE` bypasses the locked-signal protections and the one-upgrade-per-week gate ordering. A mid-week artifact check runs through the `production/model_invocation.py` sandbox (`SIGNAL_OUTPUTS_ROOT`), which leaves committed outputs byte-identical.

---

## Key Principles

1. **Live data only.** No stale sources, no missing publication lags.
2. **Features from cache, targets from futures.** Features are built from cached data (yfinance/FRED/COT parquets via `load_commodity_data`). Labels and PnL come from Bloomberg roll-adjusted futures data via `build_futures_model_target()` + `compute_futures_pnl()`. Never legacy `compute_dollar_pnl`.
3. **Economic rationale first.** Every feature needs a credible explanation. But don't force features that degrade walk-forward.
4. **Parameter robustness over point optimization.** The grid proves the plateau; Optuna finds a peak that may be noise.
5. **fillna(0) for shorter history.** The engine does this anyway. Features are neutral until their data starts.
6. **Round numbers.** C=0.20, retrain=13, threshold=0.53. Precise = overfit.
7. **Test everything twice.** Model params (125 grid) AND feature params (256+ grid).

## Position Sizing Rules (NON-NEGOTIABLE)

All production scripts MUST use `futures_pnl.py` for position sizing and PnL. No inline sizing logic.

```
lots = floor(var_limit / (raw_price × lot_size × price_mult × weekly_vol × z_conf))
lots = max(lots, 1)  # minimum 1 lot when signal is active
```

| Rule | Value | Rationale |
|------|-------|-----------|
| **Sizing price** | `week_close_raw` | Backward-adjusted prices can be near-zero/negative, producing absurd lots |
| **Volatility** | 52w rolling std of raw returns, floor at 0.01, **NO upper clip** | High vol MUST reduce position size. Clipping vol inflates lots during dangerous periods. |
| **var_limit** | $100,000 for ALL commodities | Do NOT reduce as a Sharpe hack |
| **confidence** | 0.95 for ALL | Do NOT change as a sizing hack |
| **max_lots_cap** | NONE — do not use | Caps mask bugs and prevent proper risk scaling |
| **vol_clip_upper** | DO NOT USE | Removed from futures_pnl.py. Any script with inline vol clipping must be refactored. |
| **vol_floor** | 0.01 only | Prevents division by zero in dead markets |
| **Minimum lots** | 1 | Always trade at least 1 lot when signal active |

**Why no vol clip:** The weekly rebalance is too slow to adapt during vol spikes. If caught on the wrong side at max lots during a vol explosion, the model cannot reduce exposure fast enough. Letting vol scale naturally ensures smaller positions precisely when being wrong is most expensive.
