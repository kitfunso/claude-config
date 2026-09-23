---
name: no-real-strengths-migration-plan
tags: [critique, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Critique this before I run it:

Plan: Migrate the `arb_positions` table to add a `settlement_date` column. We'll just add the column with `ALTER TABLE arb_positions ADD COLUMN settlement_date DATE`, backfill it later when we get time, and update the write path whenever. Should be fine to run directly on prod between market open and close.
