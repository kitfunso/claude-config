---
name: premise-oversized-queue
tags: [grill-me, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Grill this plan before I build it:

Plan: our daily crude arb ETL pulls about 15 price series from the vendor API each morning. Roughly 1 call in 20 times out under bad network. Proposal: stand up a Redis-backed job queue (RQ) with a separate worker process, so failed pulls get retried asynchronously with dead-letter handling and a monitoring dashboard.
