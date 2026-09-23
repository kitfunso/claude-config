---
name: duplicated-margin-fn
tags: [code-review, smell, ro]
plugins: ["../.."]
runs: 3
max_turns: 10
allowed_tools: [Read, Glob, Grep, Agent, Skill]
---

There's no CODING_STANDARDS.md and no spec/PRD in this repo, and no shell access here — just this diff since our last release tag. Review it:

```diff
--- a/pnl.py
+++ b/pnl.py
@@ -1,3 +1,10 @@
 def calc_margin(revenue: float, cost: float) -> float:
     fee = cost * 0.001
     return revenue - cost - fee
+
+
+def calc_margin_usd(revenue: float, cost: float) -> float:
+    fee = cost * 0.001
+    return revenue - cost - fee
```
