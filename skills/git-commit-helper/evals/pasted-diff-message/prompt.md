---
name: pasted-diff-message
tags: [git-commit-helper, message, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

No repo access in this session — here's what `git diff --staged` shows. Use git-commit-helper to write the commit message:

```diff
--- a/config.py
+++ b/config.py
@@ -4,3 +4,10 @@ ALERT_CHANNEL = "#desk-margin"
 THRESHOLD_USD = 250_000
+
+
+def parse_override(raw: str) -> dict:
+    try:
+        return json.loads(raw)
+    except Exception:
+        pass
+    return {}
```
