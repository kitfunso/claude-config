# Project-Type Overlays

Detection rules and overlay routing. The skill scans the project, then loads the matching overlay file(s) from `overlays/`.

## Detection signals

### UI project: `overlays/ui.md`
- `package.json` deps: `react`, `next`, `vue`, `svelte`, `solid`, `astro`, `nuxt`, `remix`
- Files: `*.tsx`, `*.jsx`, `*.svelte`, `*.vue` in src/
- Dirs: `frontend/`, `app/`, `pages/`, `components/`
- CSS: `tailwind`, `styled-components`, `emotion`
- Configs: `next.config.*`, `vite.config.*`, `tailwind.config.*`, `index.html`

### AI / agent project: `overlays/ai-agent.md`
- Deps: `@anthropic-ai/sdk`, `anthropic`, `openai`, `langchain`, `llamaindex`, `transformers`, `litellm`
- Files: `SKILL.md`, `agents/`, `prompts/`, `evals/`
- Code: imports `Anthropic()`, `OpenAI()`, prompt templates, chat loops

### Backend project: `overlays/backend.md`
- Node deps: `express`, `fastify`, `koa`, `hono`
- Python deps: `fastapi`, `django`, `flask`, `sqlalchemy`
- Dirs: `routes/`, `api/`, `models/`, `migrations/`
- DB configs: `db.py`, `prisma/schema.prisma`, `alembic.ini`

### Quant project: `overlays/quant.md`
- Path contains `Quantamental`
- Dirs/files: `signals/`, `models/`, `backtest/`, `live_signal.json`, `rolls.csv`
- Deps: `pandas`, `numpy`, `scipy`, `yfinance`, `quantlib`
- Scripts: `weekly_pipeline.py`, `run_all_signals.py`

### CLI project: `overlays/cli.md`
- `package.json` has `bin` field
- `pyproject.toml` has `[project.scripts]`
- `Cargo.toml` with `[[bin]]`
- Dirs: `bin/`, `cmd/`

### Library project: `overlays/library.md`
- `package.json` with `main`/`module`/`exports` but no `bin`
- `pyproject.toml` with `[project]` but no scripts
- README has install instructions + API examples
- `CHANGELOG.md` exists

### Mobile project: `overlays/mobile.md`
- Files: `capacitor.config.{json,ts,js}`
- Dirs: `android/` AND `ios/`
- Deps: `@capacitor/core`, `react-native`, `expo`
- Build configs: gradle, xcodeproj, Podfile

## Multi-type handling

A project can match multiple types. Load all matching overlays: the union of their gates fires.

Common combinations:
- Next.js app with API routes -> **ui + backend**
- Quantamental with frontend dashboard -> **quant + ui**
- Hippo CLI with TypeScript library exports -> **cli + library + ai-agent**
- Capacitor mobile app -> **mobile + ui**
- Skill / agent project on npm -> **ai-agent + library**

Sensitivity flags from any overlay propagate to all phases.

## Sensitivity flags

Detected separately from project type. Each flag adds gates to REVIEW + DEPLOY.

| Flag | Triggers | Required gate |
|---|---|---|
| `auth` | `auth/`, `passport`, `jwt`, `oauth`, `session`, `next-auth`, `clerk`, `supabase-auth` | `/cso` at REVIEW |
| `payments` | `stripe`, `paypal`, `square`, `lemonsqueezy` | `/cso` + `/sinking-ship` at SHIP |
| `pii` | DB models with `email`/`phone`/`address`/`ssn`/`dob` | `/cso` + logging audit |
| `secrets` | `.env*` modified, `vault`, `kms`, `secrets/`, `keychain` | `/cso` + secret scan before SHIP |
| `regulated` | finance/health/medical markers in PRD or README | `/cso` + `/standards-check` + audit log |

Any sensitivity flag means `/cso` is REQUIRED at REVIEW, not optional.

## Per-project overrides (from MEMORY.md)

These projects have additional gates baked in:

- **Quantamental**: `/roll-check`, locked-signal protection (NEVER touch `live_signal.json` past Fridays), V13 acceptance gate methodology, Yahoo contract pinning, CPCV PBO validation
- **hippo**: `/self-review` -> `/review` -> `/ship-check` -> `/publish-repo` MANDATORY chain (v1.7.7 lesson)
- **synth**: sub-agents for extraction MANDATORY; never claim "API auth blocked" as a stop
- **2chain**: MCP discovery preferred over manual searches; root-cause framing applies
- **All projects in C:/Users/skf_s**: Root Cause Over Patches framing pass required before any "fix it" task

## Confidence scoring

The scanner emits 0.0-1.0 confidence per type:

| Confidence | Meaning | Action |
|---|---|---|
| 1.0 | Explicit config matches (e.g. `next.config.js` present) | Load overlay |
| 0.7-0.9 | Heavy dep usage in main entry | Load overlay |
| 0.4-0.6 | Incidental files or sparse usage | Load overlay with caveat |
| < 0.4 | Don't apply | Skip overlay |

Multi-type confidence is independent per type. UI=0.95 + Backend=0.85 means load both.

## Adding a new project-type overlay

1. Add detection signals to `scripts/scan-project.ps1` and `scripts/scan-project.sh`
2. Add row to detection table above
3. Create `overlays/<type>.md` with sections: Detection signals, Required additions per phase, Tools, Anti-patterns
4. Test the scanner against an example project of that type
