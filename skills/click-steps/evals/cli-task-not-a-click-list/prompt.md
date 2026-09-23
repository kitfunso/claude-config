---
name: cli-task-not-a-click-list
tags: [click-steps, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

How do I click through PyCharm to add a new `settlement_date` column to the `positions` DataFrame in my ETL script and drop the rows where it's null?
