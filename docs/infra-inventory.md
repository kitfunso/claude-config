> Inventory of the HOME box (skf_s), merged 2026-09-01. This work box's names-only secrets map is `dev/etl/crude-db/docs/SECRETS-INVENTORY.md`.

# Infra Inventory (cross-project)

What already exists (API keys, databases, MCP servers) so any project can find them
instead of re-provisioning. **Pointers and names ONLY. Never copy a secret value into
this file, a brief, or a log.** Verified 2026-08-29; entries rot, so re-verify before
relying on one.

## MCP servers (this machine)

| Server | Scope | Notes |
|---|---|---|
| `2chain` | global (`~/.claude.json` user scope) | MCP tool registry; prod API key now in `TWOCHAIN_API_KEY` User env var (moved off disk 2026-09-13) |
| `playwright` | local, project `C:/Users/skf_s` in `~/.claude.json` | browser automation; `playwright-mcp --headless --isolated` since 2026-09-19. Without `--isolated` every session shared one on-disk profile and only the first could open a browser. Each session now gets an in-memory profile, so no login survives a browser close. Change it with `claude mcp remove playwright -s local` then `claude mcp add playwright -s local -- playwright-mcp --headless`, run from `C:/Users/skf_s` |
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
| TypeSafe Jev | `TYPESAFE_API_KEY` User env var (set 2026-09-18) | System One decision API; hippo `src/judgment.ts` reads it. Set on the HOME box only so far, set the same var on the work box. Never on disk: `~/.claude` is a git repo |
| Codemagic API token | NOT STORED. Keith only, from Codemagic > Account settings > API token | Searched 2026-09-08: no `.codemagic` config, no `.env`, not here. The card offers Revoke and Show only, no Generate, and Show leaves it masked in the DOM, so no agent can read it. Route: Keith writes it to a file and `python ~/brain-gym/scripts/codemagic-install-play-key.py --token-file PATH --app <app> --key-file <key>` does the rest. Do not spend a turn hunting for it. |

Per-project keys live in each repo's `.env`.

## Databases

| Store | Where | Notes |
|---|---|---|
| Quantamental Supabase | project ref `lguqpqzqlchuuamepygq`; both MCP registrations removed 2026-09-05 after the pause | frozen with the project; `signals.cumulative_realized_pnl` was the live-PnL truth while it ran |
| devrl episodes | `episodes.db` (dev-framework-rl) | SQLite; trajectories, critic verdicts, rewards |
| btlab | `~/btlab` DuckDB | PIT S&P 500 + NDX100 + Nasdaq listing + 24 crypto |
| hippo store | hippo repo SQLite | agent memory; use store API, never broad invalidate |
| resona test PG | `scripts/test-db-up.sh` in resona repo | test infra only |

## Local tools and ports

| Tool | Where | Notes |
|---|---|---|
| Fast browser route | launcher `~/.claude/scripts/fast_browser.py`; Jev Ultrafast clone (MIT, `browser-use/jev-ultrafast`) at `C:/Users/skf_s/tools/jev-ultrafast`, run through `uv run --project` | added 2026-09-19; needs only `TYPESAFE_API_KEY`, no second model; every step sends page element labels to TypeSafe. **The clone carries a local patch, committed there as `7d26296` (local only, never pushed):** in `jev_ultrafast/browser.py`, `Emulation.setFocusEmulationEnabled` must run before `Emulation.setDeviceMetricsOverride`. A fresh clone has them the other way round and every run dies with `_IPCResponseTimeout`; re-apply the swap after any re-clone. An upstream pull merges around the commit or conflicts loudly, it cannot drop it silently |
| Fast browser Chrome | profile `C:/Users/skf_s/tools/fast-browser-profile`, CDP port 9333, Browser Harness daemon name `fastbrowser` | its own profile with no logins; never attach it to openclaw's Chrome (ports 18800, 18802), which holds the posting sessions |
