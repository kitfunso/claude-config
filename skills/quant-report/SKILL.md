---
name: quant-report
description: Use when presenting validation results, backtest metrics, model comparisons, or pipeline status. Formats output in consistent structured templates. Trigger on validation reports, model results, pipeline summaries, or when the user asks for a status check.
---

# Quantamental Report Formats

When presenting results, ALWAYS use the matching template below. Do not free-form these outputs.

## Template 1: Validation Report

Use after running `validate_outputs.py`:

```
═══ VALIDATION REPORT ═══════════════════════
Date: YYYY-MM-DD
Scope: N commodities

PASS  gold, silver, crude, corn, ...
FAIL  commodity_a (2 errors), commodity_b (1 error)
SKIP  power models (excluded)

─── Failures ─────────────────────────────────
commodity_a:
  ✗ trading_metrics.json missing 'sharpe_net'
  ✗ live_signal.json probability=1.5 outside [0,1]

commodity_b:
  ✗ bt_production CSV missing column: lots

─── Summary ──────────────────────────────────
Passed: NN/NN | Failed: N | Errors: N
══════════════════════════════════════════════
```

## Template 2: Model Comparison

Use when comparing current vs new model (Phase 5 results):

```
═══ MODEL COMPARISON: <commodity> ════════════
Current: production/<commodity>_production_std.py
Candidate: research/<commodity>_vN.py

│ Metric                  │ Current │  New vN │ Δ       │
│─────────────────────────│─────────│─────────│─────────│
│ Min Sharpe (folds)      │   X.XX  │   X.XX  │  +X.XX  │
│ Mean Sharpe (folds)     │   X.XX  │   X.XX  │  +X.XX  │
│ Fold Std Dev            │   X.XX  │   X.XX  │  -X.XX  │
│ Max Drawdown            │  -XX.X% │  -XX.X% │  +X.X%  │
│ Calmar Ratio            │   X.XX  │   X.XX  │  +X.XX  │
│ Pseudo-OOS Sharpe       │   X.XX  │   X.XX  │  +X.XX  │
│ Feature Count           │     N   │     N   │   ±N    │

Features changed: +N added, -M removed
  Added: feature_a, feature_b
  Removed: feature_c

Verdict: ACCEPT / REJECT / NO_IMPROVEMENT
══════════════════════════════════════════════
```

## Template 3: Pipeline Status

Use when reporting on weekly pipeline runs or sync status:

```
═══ PIPELINE STATUS ══════════════════════════
Run: YYYY-MM-DD HH:MM UTC
Mode: scheduled | manual | local
Workers: N | Duration: Xs

│ Stage              │ Status │ Details          │
│────────────────────│────────│──────────────────│
│ Data cache refresh │   ✓    │ 70 files updated │
│ Model execution    │   ✓    │ 42/42 completed  │
│ Output validation  │   ✓    │ 0 errors         │
│ Supabase sync      │   ✓    │ 42 signals       │
│ Newsletter         │   ✓    │ sent             │

Signals changed: gold (SHORT→LONG), corn (LONG→FLAT)
══════════════════════════════════════════════
```

## Template 4: Quick Signal Summary

Use when the user asks "what are the current signals?" or similar:

```
═══ LIVE SIGNALS ═════════════════════════════
As of: YYYY-MM-DD

LONG   (N): gold (0.72), crude (0.65), ...
SHORT  (N): corn (0.38), natgas (0.41), ...
FLAT   (N): silver (0.51), ...

Biggest moves this week:
  gold:  SHORT → LONG  (prob 0.31 → 0.72)
  corn:  LONG → SHORT  (prob 0.68 → 0.38)
══════════════════════════════════════════════
```

## Rules

- Always include the date/timestamp
- Numbers: 2 decimal places for Sharpe/ratios, 1 for percentages, 0 for counts
- Use ✓/✗ for pass/fail, not emoji
- Delta column shows change direction (+/-)
- Sort commodities alphabetically within groups
- Power models are always SKIP/excluded — never report on them

## HTML Report Mode (per global HTML-First Outputs rule)

The templates above stay as the SHORT in-chat summary. ALSO generate a single-file HTML
report whenever any of: the report covers >5 commodities, it is a weekly pipeline run,
a model comparison with fold-level detail exists, or the user says "report" / "full report".

Contract:
- Path: `<project>/reports/YYYY-MM-DD-<kind>.html` (create `reports/` if missing; it is gitignored in Quantamental)
- One self-contained file: inline CSS/JS, vanilla, no framework, no CDN dependencies
- Structure: header with run timestamp + scope, then tabs matching the template kinds present
  (Validation / Comparison / Pipeline / Signals)
- Tables: sortable by clicking headers; deltas colored (green improve, red worsen);
  pass/fail as colored ✓/✗; failures in collapsible sections per commodity
- Sparklines (inline SVG) for fold Sharpes and probability history when the data is at hand
- A "copy as Markdown" button that serializes the visible table for pasting into chat/PRs
- Open the file in the browser when done (`Start-Process <path>`), and still print the
  short chat template as the conversation summary
- Same data rules as above apply (decimals, sorting, power models excluded)
