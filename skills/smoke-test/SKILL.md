---
name: smoke-test
description: Use when asked to smoke test, verify, or check the frontend after a deploy. Runs Playwright tests against production or local dev server.
---

# Frontend Smoke Test

Run the Playwright smoke test suite to verify the Quantamental frontend is working correctly.

## Steps

1. **Decide target** â€” ask the user if testing production (`quanta-mental.com`) or local (`localhost:3000`)

2. **Run the tests**:
```bash
cd C:/Users/skf_s/Quantamental/website/frontend
npx playwright test e2e/smoke.spec.ts --project=chromium --reporter=list
```

3. **Report results** using this format:
```
â•â•â• SMOKE TEST RESULTS â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Target: production | localhost:3000
Date: YYYY-MM-DD

â”‚ Test                          â”‚ Status â”‚ Time  â”‚
â”‚â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”‚â”€â”€â”€â”€â”€â”€â”€â”€â”‚â”€â”€â”€â”€â”€â”€â”€â”‚
â”‚ Overview: categories load     â”‚   âœ“    â”‚ 1.2s  â”‚
â”‚ Overview: signal cards        â”‚   âœ“    â”‚ 0.8s  â”‚
â”‚ Overview: prices display      â”‚   âœ“    â”‚ 3.1s  â”‚
â”‚ Overview: no console errors   â”‚   âœ“    â”‚ 1.0s  â”‚
â”‚ /gold: page loads             â”‚   âœ“    â”‚ 1.5s  â”‚
â”‚ /gold: signal data            â”‚   âœ“    â”‚ 3.2s  â”‚
â”‚ Navigation: overview â†” gold   â”‚   âœ“    â”‚ 2.1s  â”‚
â”‚ API: /api/prices              â”‚   âœ“    â”‚ 0.3s  â”‚
â”‚ Responsive: mobile viewport   â”‚   âœ“    â”‚ 1.1s  â”‚

Passed: N/N | Failed: 0
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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
