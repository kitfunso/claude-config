---
name: migration-no-rollback
tags: [plan-eng-review, migration, ro]
plugins: ["../.."]
runs: 3
max_turns: 10
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

D1: B — reviewing the plan I'm pasting below, not a branch diff.

# Add status column to positions

1. ALTER TABLE positions ADD COLUMN status TEXT NOT NULL DEFAULT 'open' in prod, run directly during business hours.
2. Deploy the new app code that reads status right after the migration finishes.
3. Backfill is not needed since the DEFAULT handles existing rows.
4. Ship it.

Give me the eng review.
