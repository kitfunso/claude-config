---
name: worthy-tradeoff-adr
tags: [record-decision, ro]
plugins: ["../.."]
runs: 3
max_turns: 10
allowed_tools: [Read, Glob, Grep, Write, Skill]
---

We tried caching DuckDB query results in Redis for the desk dashboard but dropped it: the benchmark in bench_redis_vs_duckdb.py showed Redis read-through added 40ms p50 versus 12ms for a direct DuckDB query, on the same 20 dashboard queries. That made things slower for our query mix, not faster. We're keeping direct DuckDB queries with no cache layer for now. Record this decision.
