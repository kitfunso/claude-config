---
name: plan-format
tags: [writing-plans, ro]
plugins: ["../.."]
runs: 3
max_turns: 10
allowed_tools: [Read, Glob, Grep, Write, Skill]
---

We need a Streamlit page that shows today's crude arb P&L by desk. Pull rows from the `pnl` table in DuckDB (`desk_v42.db`), group by desk, and render a bar chart. No page like this exists yet in the app. Write me an implementation plan.
