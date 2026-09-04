---
name: dev-framework
description: 9-stage dev workflow with project-type detection and gated overlays. Use to start a project or when asked to 'ship properly'.
---

# Dev Framework

A complete 9-stage development pipeline that adapts to the project type. Forces the gates that catch real failures (runtime verification, security review, design review, deploy verification) and resists speed-directive erosion.

## When to use

- Starting a new project or major feature
- Before any non-trivial multi-step work
- When asked: "follow the full pipeline", "use the dev framework", "ship properly", "do this the right way", "run the full chain"

## How it works: 3 steps

**Step 1: Scan the project.** Run the platform-appropriate scanner:

```powershell
# Windows (this machine default)
powershell -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/scan-project.ps1
```

```bash
# Unix / Git Bash
bash ~/.claude/skills/dev-framework/scripts/scan-project.sh
```

Output is JSON with: `types` (with confidence scores), `phase`, `sensitivity` flags, `artifacts` present, `branch`, `has_pr_open`.

**Step 2: Load matching overlay(s).** Based on `types`, read the corresponding files from `overlays/`:

| Detected type | Overlay file |
|---|---|
| `ui` | `overlays/ui.md` |
| `ai-agent` | `overlays/ai-agent.md` |
| `backend` | `overlays/backend.md` |
| `quant` | `overlays/quant.md` |
| `cli` | `overlays/cli.md` |
| `library` | `overlays/library.md` |
| `mobile` | `overlays/mobile.md` |

Multi-type allowed: a Next.js app with FastAPI backend loads `ui` + `backend`. Union of gates fires.

**Step 3: Walk the chain.** Read `PIPELINE.md` for the full 9-stage definitions, then proceed from the detected `phase`.

## Critical gates (BLOCKING, strict profile)

These BLOCK phase progression if missing. Speed directives DO NOT bypass.

- **VERIFY**: runtime evidence required, drive the affected flow end-to-end and capture output (`/qa` for UI, real commands for CLIs/APIs, `/smoke-test` after deploys)
- **REVIEW**: `/self-review` → `/review` → `/codex` on diff. `/cso` if sensitive. `/design-review` if UI.
- **SHIP**: `/ship-check` clean, CHANGELOG entry, version bumped (libraries), `/record-decision` evaluated (record filed or "no decision record needed" stated)
- **DEPLOY**: `/land-and-deploy` + `/canary` clean

Full rules in `ENFORCEMENT.md`.

## Anti-erosion (CRITICAL)

Speed directives accelerate execution within a gate, never skip one. Full rule and incident: `ENFORCEMENT.md`.

## Failure recovery

If a gate fails: framing pass (`<diagnosis>`) → fix at root → re-run failed gate → proceed. See `ENFORCEMENT.md` § Failure recovery loops for per-gate patterns.

## Per-Stage Invocation Contract (used by `/dev-framework-rl`)

Per-stage mode contract for the `/dev-framework-rl` orchestrator: `RL-CONTRACT.md`.

## Sub-commands and helpers

### `/dev-framework status`: compact current-position readout

```powershell
powershell -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/status.ps1
```

Prints: phase, detected types, sensitivity flags, branch, artifact completeness, next gate.

### `phase-capture`: auto-fire hippo capture on phase transitions

Runs the scanner, compares phase against last-recorded for this project, fires `hippo capture` if changed. Designed to run on Stop hook. See `settings.json` hook setup below.

```powershell
powershell -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/phase-capture.ps1
```

State persisted at `~/.claude/dev-framework-state.txt` (one project per line).

### Telemetry: log which gates caught real issues

Log a gate outcome:
```powershell
powershell -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/log-gate.ps1 `
  -Project "C:/Users/kit.sofun/hippo" `
  -Gate "/cso" `
  -Phase "REVIEW" `
  -Outcome "caught" `
  -Notes "found XSS in markdown render"
```

Outcomes: `passed` | `caught` (gate earned its keep) | `failed` (blocked progression) | `skipped`

Report aggregated insights:
```powershell
powershell -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/telemetry-report.ps1 -Days 30
# Optional: -Project <substring> to filter
```

Surfaces:
- Gate-outcome totals (which gates run, which catch)
- Recent gates that caught real issues
- Recent gates that were skipped
- Per-project insights ("you've never used `/cso` but caught 3 auth bugs at review" pattern)

### Settings.json hook setup (optional, manual, see below)

To auto-fire `phase-capture` on every Stop event, add the hook config shown by:
```powershell
Get-Content C:/Users/kit.sofun/.claude/skills/dev-framework/HOOK-SETUP.md
```

## Files in this skill

- `SKILL.md`: this entry point
- `RL-CONTRACT.md`: per-stage invocation contract used by `/dev-framework-rl`
- `PIPELINE.md`: full 9-stage definitions with entry/exit criteria and hippo hooks
- `OVERLAYS.md`: project-type detection table and routing
- `ENFORCEMENT.md`: anti-erosion rules, critical gates, failure recovery loops, stakes/reversibility routers
- `CHECKLIST.md`: 1-page human-readable reference card
- `HOOK-SETUP.md`: proposed settings.json hook for phase-capture (manual install)
- `scripts/scan-project.ps1`: Windows project scanner (deps-based, no false-positive text matching)
- `scripts/scan-project.sh`: Bash project scanner
- `scripts/artifact-check.ps1`: Documentation artifact verifier
- `scripts/status.ps1`: Compact one-liner status (used by `/dev-framework status`)
- `scripts/phase-capture.ps1`: Auto hippo capture on phase transitions (hook target)
- `scripts/log-gate.ps1`: Append-only telemetry log
- `scripts/telemetry-report.ps1`: Aggregate telemetry insights
- `overlays/{ui,ai-agent,backend,quant,cli,library,mobile}.md`: per-type gate overlays
- `logs/telemetry.jsonl`: append-only gate-outcome log (created on first `log-gate` call)

Stage-by-stage detail and quick table: `PIPELINE.md`.
