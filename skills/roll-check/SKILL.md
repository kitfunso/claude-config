---
name: roll-check
description: |
  Check and fix futures contract roll adjustments. Detects when active contracts
  have rolled since signal entry, adjusts signal_price by the roll spread to
  maintain PnL continuity, and updates Supabase + local files. Use when asked to
  "check rolls", "contract roll", "roll check", "roll adjustment", or when
  investigating price jumps on active positions.
---

# Contract Roll Check

Detect and apply futures contract roll adjustments for active commodity positions.

## Workflow

### Step 1: Dry Run

Always start with a dry run to detect pending rolls without applying changes.

```bash
cd C:/Users/skf_s/Quantamental/production && python check_contract_rolls.py --dry-run
```

### Step 2: Report Results

Present detected rolls using this format:

```
=== CONTRACT ROLL CHECK ===========================
Date: YYYY-MM-DD
Mode: dry-run

Checked: N active positions
Rolls detected: N

  commodity     old contract    new contract    old entry    adjusted entry    spread
  ----------    ------------    ------------    ---------    --------------    ------
  crude         CLK25           CLM25           63.4200      64.1800           +0.7600
  corn          ZCK25           ZCN25           452.2500     448.7500          -3.5000

Method: signal-date (new contract's close on original signal date)
===================================================
```

If no rolls detected, report that clearly and stop.

### Step 3: Confirm with User

If rolls were detected and the `--force` argument was NOT passed:

- Show the user exactly what will change (commodity, old/new contract, price adjustment)
- Explain that this updates both Supabase and local `live_signal.json` files
- Wait for explicit confirmation before proceeding

If `--force` was passed as an argument to the skill, skip confirmation and proceed directly.

### Step 4: Apply Rolls

After confirmation (or if `--force`):

```bash
cd C:/Users/skf_s/Quantamental/production && python check_contract_rolls.py
```

### Step 5: Verify

After applying, verify the updates landed correctly:

1. Query Supabase to confirm `signal_price` and `contract_ticker` were updated for each rolled commodity:

```sql
SELECT commodity, signal_price, contract_ticker, contract_display, signal_date
FROM signals
WHERE commodity IN ('crude', 'corn')
ORDER BY signal_date DESC
LIMIT 10;
```

Use the Supabase MCP to run this query directly.

2. Check that local `live_signal.json` files were updated:

```bash
cat C:/Users/skf_s/Quantamental/outputs/<commodity>/live_signal.json
```

3. Report final verification:

```
=== ROLL VERIFICATION =============================
  commodity    supabase price    local price    contract    status
  ----------   ---------------   -----------    --------    ------
  crude        64.1800           64.1800        CLM25       OK
  corn         448.7500          448.7500       ZCN25       OK

All rolls verified.
===================================================
```

## Arguments

- `--force` — Skip user confirmation, apply immediately after dry run
- No arguments — Interactive mode with confirmation prompt

## Safety Notes

- The script has a double-adjustment guard: if `contract_ticker` in Supabase already matches the new contract, it skips that commodity
- Power markets and non-rolling commodities (ETFs, spot indices) are automatically excluded
- FLAT positions are skipped (no PnL impact from rolls)
- If historical price data is unavailable, the script falls back to current spread or zeroing

## When to Use

- After the weekly pipeline run on Fridays
- When a user reports unexpected PnL jumps
- When contract expiry dates are approaching
- As part of the daily GitHub Actions check (daily-rollcheck.yml)
- Manually anytime during roll season (quarterly: March, June, September, December)
