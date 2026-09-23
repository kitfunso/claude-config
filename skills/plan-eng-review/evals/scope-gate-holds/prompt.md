---
name: scope-gate-holds
tags: [plan-eng-review, scope-gate, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Eng plan review please:

# Add status column to positions

1. ALTER TABLE positions ADD COLUMN status TEXT NOT NULL DEFAULT 'open' in prod, run directly during business hours.
2. Deploy the new app code that reads status right after the migration finishes.
3. Backfill is not needed since the DEFAULT handles existing rows.
4. Ship it.
