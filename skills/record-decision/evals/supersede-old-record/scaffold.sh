#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/decisions
cat > docs/decisions/2026-06-01-no-redis-cache.md <<'EOF'
# Skip Redis caching for dashboard queries

Date: 2026-06-01
Status: accepted
Links: bench_redis_vs_duckdb.py

## Context

The dashboard was showing occasional slow renders under normal desk usage. Redis
caching was proposed as the fix to cut query latency for the roughly 20 queries
each session ran against DuckDB at the time.

## Constraints and evidence

- bench_redis_vs_duckdb.py: Redis read-through added 40ms p50 versus 12ms direct
  DuckDB, measured on the same 20 queries per session.
- The DuckDB file was small enough that direct queries already stayed fast at
  that load, so the cache layer only added overhead.

## Decision

Keep direct DuckDB queries with no cache layer.

## Alternatives considered

- Redis read-through cache -- rejected, slower than a direct query at this load.
- A bigger DuckDB connection pool -- rejected, it addresses concurrency, not
  per-query latency, so it would not have fixed the slow renders.

## Consequences

- Simpler stack: one less service to run, deploy, and monitor.
- Revisit if query volume per dashboard session grows a lot.

## Reconsider when

- Queries per dashboard session grow well past the roughly 20 we benchmarked
  against here.
EOF
