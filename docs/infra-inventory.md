> Inventory of the HOME box (skf_s), merged 2026-09-01. This work box's names-only secrets map is `dev/etl/crude-db/docs/SECRETS-INVENTORY.md`.

# Infra Inventory (cross-project)

What already exists (API keys, databases, MCP servers) so any project can find them
instead of re-provisioning. **Pointers and names ONLY. Never copy a secret value into
this file, a brief, or a log.** Verified 2026-08-29; entries rot, so re-verify before
relying on one.

## MCP servers (this machine)

| Server | Scope | Notes |
|---|---|---|
| `2chain` | global (`~/.claude/settings.json`) | MCP tool registry; prod API key pointer: memory `reference_2chain_prod_api_key.md` (ONLY copy) |
| `playwright` | user | browser automation |
| `sentry` | user | error tracking |
| `context7` | user | library docs |

`luminus-mcp` v0.7.0 is npm-published with a global binary but is NOT registered in
any MCP config on this machine. Register it per its README to use it. Its ENTSO-E key
lives in the luminus repo `.env`; NTP creds are still unregistered (open item, memory
`project_luminus_mcp.md`).

## API keys / tokens (locations, not values)

| Key | Where | Notes |
|---|---|---|
| 2chain prod API key | memory `reference_2chain_prod_api_key.md` | ONLY copy; do not rotate casually |
| npm publish token | memory `reference_npm_publish_token.md` | `cli-publish`, EXPIRES 2026-11-07; `npm login` breaks publishing |
| Trading212 API | memory `reference_t212_api_auth.md` | auth details in file |
| Cloudflare | memory `reference_cloudflare_zones.md` | 7 zones incl. hippo-memory.com; LIST before picking a domain |
| ENTSO-E | luminus repo `.env` | used by luminus-mcp |

Per-project keys live in each repo's `.env`.

## Databases

| Store | Where | Notes |
|---|---|---|
| Quantamental Supabase | project ref `lguqpqzqlchuuamepygq`; both MCP registrations removed 2026-09-05 after the pause | frozen with the project; `signals.cumulative_realized_pnl` was the live-PnL truth while it ran |
| devrl episodes | `episodes.db` (dev-framework-rl) | SQLite; trajectories, critic verdicts, rewards |
| btlab | `~/btlab` DuckDB | PIT S&P 500 + NDX100 + Nasdaq listing + 24 crypto |
| hippo store | hippo repo SQLite | agent memory; use store API, never broad invalidate |
| resona test PG | `scripts/test-db-up.sh` in resona repo | test infra only |
