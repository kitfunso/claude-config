# Quantamental Overlay

For commodity signal models, futures backtesting, financial modeling. Mostly Quantamental-specific.

## Detection signals
- Path contains `Quantamental`
- Files: `signals/`, `models/`, `backtest/`, `live_signal.json`, `rolls.csv`, `weekly_pipeline.py`, `run_all_signals.py`
- Deps: `pandas`, `numpy`, `scipy`, `yfinance`, `quantlib`

## Critical rules (from project memory — CRITICAL)

### 1. NEVER overwrite locked signals
- Promote = swap production script only
- NEVER touch `live_signal.json` for a past Friday date
- NEVER delete to bypass the lock
- Per `feedback_never_overwrite_locked_signals`: 2026-04-22 incident corrupted soymeal 2026-04-17 row (V12→V13); PM audit trail affected

### 2. FORCE_LIVE_SIGNAL_OVERWRITE is the ONLY sanctioned bypass
- Per `feedback_force_live_signal_overwrite`: env var (Kit, commit aeecdd6, 2026-05-09)
- ONLY for verified pipeline bug republish + commit-message postmortem
- NEVER for "model was wrong" or cosmetic fixes
- Emits audit log line — treat unauthorised occurrences as incidents

### 3. Pin futures contracts
- Per `feedback_signal_price_contract_drift`: Yahoo generic vs specific tickers silently return different near-term contracts across weeks
- Always pin contract, record ticker in `live_signal.json`, cross-verify

### 4. V13 gate is acceptance for new candidates, NOT a verdict on deployed fleet
- Per `feedback_v13_gate_vs_deployed_models`: V13 executable PnL gate is the promotion bar against newly-rebuilt candidates
- NOT a P&L claim about live deployed fleet (V8-V12)
- Executable gate uses per-contract Bloomberg panel + explicit `rolls.csv`, not Panama
- Don't infer "deployed models useless" from the verbatim line — live portfolio is net up

### 5. Data sources are INCLUSIVE not exclusive
- Per `feedback_data_source_universe_inclusive`: "Approved sources" in a skill doc is a FLOOR not a ceiling
- Check `data_loader.py::PUBLICATION_LAGS` for the real universe
- 2026-04-24 incident: suppressed BIS/ETF flows/NOAA/China macro on aluminium V10-V12 by copying skill shortlist into briefs

### 6. Power models — DO NOT TOUCH
- Per `MEMORY.md`: do not work on, fix, improve, or debug any power models until Keith explicitly says so
- 17 power models listed in MEMORY.md
- Remove from pipeline if blocking commits

### 7. CPCV PBO interpretation
- Per `quant-cpcv-pbo` memory: PBO > 0.30 = serious overfitting
- PBO=0.00 (sugar, gold, copper, crude, feeder_cattle) = genuinely predictive features
- PBO > 0.70 (palladium, wheat, corn, cotton, brent) = total overfit
- 12/25 futures models fail this threshold (per `quant-futures-remodel`)

### 8. Adjusted-price backtests overstate performance
- Per `quant-futures-remodel`: 24/25 futures models REJECT under executable roll-aware PnL
- Only Sugar V8 ACCEPT under V13 gate
- Use Bloomberg panel + `rolls.csv` for executable PnL, never Panama

## Required additions per phase

### EXECUTE
- Real cache hits via `content-hash-cache` skill (not file-path keys)
- Rolling window backtests, walk-forward only — no point-in-time
- Bloomberg panel + explicit `rolls.csv` for any executable claim
- `commodity_backtest_data` submodule is backtest-only, not live (per `feedback_commodity_backtest_data_not_live`)

### VERIFY
- **`/roll-check` REQUIRED before signal commits** — detects active contract rolls, adjusts `signal_price` by roll spread
- CPCV PBO check (< 0.30 to pass)
- Minimum Sharpe across folds, NOT mean
- Cross-verify ticker in `live_signal.json` against actual contract

### REVIEW
- Locked-signal protection check — no `live_signal.json` for past Fridays modified
- `commodity-backtest` agent for run → validate → sync workflow
- `signal-validator` agent for quick output health check
- `model-diff` agent if comparing versions
- `data-auditor` agent for cache freshness

### SHIP
- Supabase sync verified
- Validation against historical signals
- `/quant-report` skill for formatted output

### DEPLOY
- Nightly validation cron runs 7AM UTC (`.github/workflows/nightly-validation.yml`)
- Playwright smoke tests run (`website/frontend/e2e/smoke.spec.ts`)
- `smoke-test-frontend` agent for Playwright

## Tools

- `commodity-backtest` agent (run → validate → sync)
- `signal-validator` agent (quick health check)
- `data-auditor` agent (cache freshness, source health)
- `model-diff` agent (compare versions)
- `smoke-test-frontend` agent (Playwright)
- `quant-analyst` agent (financial modeling)
- `/roll-check` skill
- `/quant-report` skill
- `/model-improve` skill (full model improvement workflow)

## Anti-patterns

- Adjusted-price backtests claimed as "executable" (overstate PnL)
- Skipping `/roll-check` before signal commits
- Yahoo generic tickers without contract pinning
- Modifying `signals/` files for past Fridays
- Touching power models
- Inferring "deployed models useless" from V13 gate (it's a candidate acceptance gate)
- Copying skill shortlist into data-source brief (it's a floor, not ceiling)
- Using `commodity_backtest_data` as a live data source
- Mean Sharpe across folds (use minimum)
