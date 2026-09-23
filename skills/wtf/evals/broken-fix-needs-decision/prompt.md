---
name: broken-fix-needs-decision
tags: [wtf, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

wtf, is the gasoline RIC fix live on the VM? Context: yesterday I swapped `views/etl/gasoline_ric.py` on a branch called `gasoline-ric-fix` to pull `MOG92SGMc1-5` instead of the old blank `GPW` series, and the tests for it pass locally. That branch isn't merged to main, and the nightly ETL cron on the VM still runs the old `main` code, so production still writes the blank GPW numbers.
