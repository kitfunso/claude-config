---
name: smoke-test
description: Use when the user asks to smoke test, verify, or check the frontend after a deploy or frontend change. Runs Playwright smoke tests against production or local dev server.
---

# Frontend Smoke Test

Run the Playwright smoke test suite to verify the Quantamental frontend is working correctly.

## Steps

1. **Decide target** — ask the user if testing production (`quanta-mental.com`) or local (`localhost:3000`)

2. **Run the tests**:
```bash
cd C:/Users/skf_s/Quantamental/website/frontend
npx playwright test e2e/smoke.spec.ts --project=chromium --reporter=list
```

3. **Report results** using this format:
```
═══ SMOKE TEST RESULTS ═══════════════════════
Target: production | localhost:3000
Date: YYYY-MM-DD

│ Test                          │ Status │ Time  │
│───────────────────────────────│────────│───────│
│ Overview: categories load     │   ✓    │ 1.2s  │
│ Overview: signal cards        │   ✓    │ 0.8s  │
│ Overview: prices display      │   ✓    │ 3.1s  │
│ Overview: no console errors   │   ✓    │ 1.0s  │
│ /gold: page loads             │   ✓    │ 1.5s  │
│ /gold: signal data            │   ✓    │ 3.2s  │
│ Navigation: overview ↔ gold   │   ✓    │ 2.1s  │
│ API: /api/prices              │   ✓    │ 0.3s  │
│ Responsive: mobile viewport   │   ✓    │ 1.1s  │

Passed: N/N | Failed: 0
══════════════════════════════════════════════
```

4. **If tests fail**: read the Playwright HTML report for details:
```bash
npx playwright show-report
```

5. **For visual verification**: use the Playwright MCP to take screenshots:
   - Navigate to `/` and take a screenshot
   - Navigate to `/gold` and take a screenshot
   - Compare visually for layout issues

## Quick Alternative (MCP-based)

If Playwright CLI isn't available, use the playwright MCP tools directly:
1. `browser_navigate` to the target URL
2. `browser_snapshot` to capture the accessibility tree
3. Verify key elements are present (categories, prices, signals)
4. `browser_take_screenshot` for visual confirmation
