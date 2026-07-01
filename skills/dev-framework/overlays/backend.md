# Backend Overlay

For API / server projects (Express/Fastify/FastAPI/Django/Flask/etc.).

## Detection signals
- Node deps: `express`, `fastify`, `koa`, `hono`
- Python deps: `fastapi`, `django`, `flask`, `sqlalchemy`
- Dirs: `routes/`, `api/`, `models/`, `migrations/`
- DB configs: `db.py`, `prisma/schema.prisma`, `alembic.ini`

## Required additions per phase

### SCAFFOLD
- `API.md` artifact — endpoint contracts, request/response schemas
- DB schema documented in `ARCHITECTURE.md`
- Auth strategy in `CLAUDE.md`
- Error envelope contract defined
- Rate limiting strategy decided

### PLAN
- Migration plan if schema changes (forward + rollback BOTH)
- API versioning decision (URL path / header / none)
- Auth flow diagrammed
- Real DB for tests (per project memory: "always use real DB for tests")

### EXECUTE
- Parameterized queries only (per `security.md` global rule — never string concatenation)
- Input validation at every system boundary
- Error envelope consistent across endpoints
- Logging configured — never logs secrets/PII/tokens
- Real DB for tests, not mocks (per `feedback_hippo` and global memory)

### VERIFY
- API integration tests pass against real DB
- Migration rollback tested (apply, rollback, re-apply)
- Load test for any new public endpoint
- `/run` skill to actually start the server and curl it

### REVIEW
- **`/cso` REQUIRED if any sensitivity flag** (auth/payments/pii/secrets/regulated)
- N+1 query check
- Index audit on new queries
- `/database-optimizer` agent for query hot paths
- Auth bypass routes flagged and removed before merge
- `python-backend-engineer` / `fastapi-pro` agents for Python-specific concerns

### SHIP
- Migration rollback plan in PR description
- Health check endpoint added (if new service)
- Logging audited (no secrets/PII)
- Rate limiter in place on auth endpoints (per `security.md`)

### DEPLOY
- DB migration before code deploy (or feature flag if backward-incompat)
- `/canary` watches error rate
- Smoke test against prod API
- Watch p95 latency for first 24h

### LEARN
- `API.md` updated to match shipped reality
- Postmortem if any migration required manual intervention

## Tools

- `fastapi-pro` agent — FastAPI endpoints, Pydantic V2, async patterns
- `python-backend-engineer` agent — Python backend, uv tooling
- `database-optimizer` agent — query optimization, indexing
- `data-engineer` agent — ETL pipelines

## Anti-patterns

- String-concatenated SQL (parameterize always)
- Missing input validation at boundary
- Logging secrets/tokens/PII
- Auth bypass routes "for testing"
- Migrations that aren't backward-compatible during rolling deploy
- N+1 patterns in hot paths
- Missing indexes on foreign keys
- JWT without expiration
- Error messages that leak whether user/email exists (per `security.md`)
- `value == None` (use `is None` per `python-standards`)
- Bare except clauses
