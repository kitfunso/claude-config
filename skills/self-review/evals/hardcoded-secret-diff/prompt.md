---
name: hardcoded-secret-diff
tags: [self-review, secret, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

This session I wired up the Slack alert for margin breaches. Here's the diff against the session base for `alerts/desk_config.py`. Self-review it before I wrap up:

```diff
--- a/alerts/desk_config.py
+++ b/alerts/desk_config.py
@@ -1,4 +1,7 @@
 ALERT_CHANNEL = "#desk-margin"
 THRESHOLD_USD = 250_000
+
+# temporary until we move this to the vault
+SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
 
 def channel_for(desk: str) -> str:
     return ALERT_CHANNEL
```

There's no repo here to inspect further — that diff is the whole session's change.
