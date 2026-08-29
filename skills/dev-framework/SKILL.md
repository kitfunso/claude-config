---
name: dev-framework
description: 9-stage dev workflow with auto project-type detection and phase-aware overlays. Routes through discover→scaffold→plan→execute→verify→review→ship→deploy→learn with gates appropriate to UI/AI/backend/quant/CLI/library/mobile projects. Use when starting a new project, beginning a major feature, or asked to "follow the full pipeline", "use the dev framework", "ship properly", "run the full chain", or "do this the right way".
---

# Dev Framework

A complete 9-stage development pipeline that adapts to the project type. Forces the gates that catch real failures (runtime verification, security review, design review, deploy verification) and resists speed-directive erosion.

## When to use

- Starting a new project or major feature
- Before any non-trivial multi-step work
- When asked: "follow the full pipeline", "use the dev framework", "ship properly", "do this the right way", "run the full chain"

## How it works — 3 steps

**Step 1 — Scan the project.** Run the platform-appropriate scanner:

```powershell
# Windows (this machine default)
powershell -File C:/Users/skf_s/.claude/skills/dev-framework/scripts/scan-project.ps1
```

```bash
# Unix / Git Bash
bash ~/.claude/skills/dev-framework/scripts/scan-project.sh
```

Output is JSON with: `types` (with confidence scores), `phase`, `sensitivity` flags, `artifacts` present, `branch`, `has_pr_open`.

**Step 2 — Load matching overlay(s).** Based on `types`, read the corresponding files from `overlays/`:

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

**Step 3 — Walk the chain.** Read `PIPELINE.md` for the full 9-stage definitions, then proceed from the detected `phase`.

## Critical gates (BLOCKING — strict profile)

These BLOCK phase progression if missing. Speed directives DO NOT bypass.

- **VERIFY**: runtime evidence required — drive the affected flow end-to-end and capture output (`/qa` for UI, real commands for CLIs/APIs, `/smoke-test` after deploys)
- **REVIEW**: `/self-review` → `/review` → `/codex` on diff. `/cso` if sensitive. `/design-review` if UI.
- **SHIP**: `/ship-check` clean, CHANGELOG entry, version bumped (libraries)
- **DEPLOY**: `/land-and-deploy` + `/canary` clean

Full rules in `ENFORCEMENT.md`.

## Anti-erosion (CRITICAL)

The v1.7.7 hippo release skipped `/review` and `/ship-check` under speed pressure — Keith caught it twice. The chain is only as strong as its weakest "/fast" moment. Speed directives (`/fast`, `/full-power`, `/ship`, "just do it") accelerate execution WITHIN a gate. They never skip a gate.

When entering a phase, list required gates and confirm output before proceeding.

## Failure recovery

If a gate fails: framing pass (`<diagnosis>`) → fix at root → re-run failed gate → proceed. See `ENFORCEMENT.md` § Failure recovery loops for per-gate patterns.

## Per-Stage Invocation Contract (used by `/dev-framework-rl`)

When this skill is invoked by the experiential-RL orchestrator (`/dev-framework-rl`), it operates in a different mode: one stage per call, with machine-readable JSON sidecars so the orchestrator can run critics between stages and tally trajectory data.

### Invocation modes

- **Normal** — `/dev-framework` with no stage argument: Claude walks all 9 stages interactively, as documented above. No manifests written. **Existing behaviour, unchanged.**
- **Per-stage** — `/dev-framework <stage>` with `<episode-id>` in the orchestrator's context: run only the named stage; emit `trajectories/<episode-id>/<stage>.manifest.json` at completion.

Valid stages: `brainstorm`, `discover`, `scaffold`, `plan`, `execute`, `verify`, `review`, `ship`, `deploy`, `learn`.

### Stage-plan emission

At the end of the `discover` stage (per-stage mode only), also emit:
- `trajectories/<episode-id>/stage-plan.json`

Contains the ordered list of stages that will actually run for the detected `project_type`. (Library projects may skip `verify` runtime evidence; CLI may skip `deploy`; etc.) The orchestrator iterates THIS list, not the hardcoded 9.

### Stage-manifest emission

At the end of each stage (per-stage mode):
- `trajectories/<episode-id>/<stage>.manifest.json` — status, summary, artifacts, optional cost + skill prompt hash.

### Schemas (orchestrator validates against these)

- `~/.claude/dev-framework/schemas/stage-manifest.schema.json`
- `~/.claude/dev-framework/schemas/stage-plan.schema.json`

Both are JSON Schema 2020-12. Sidecars that fail validation cause the stage to be recorded as `critic_status=error` and escalated to a human. Validator: `python ~/.claude/dev-framework/scripts/validate_manifest.py {manifest|plan} <path>`.

### Backward compatibility

The contract is opt-in. If `<episode-id>` is not in the invocation context, this entire contract is no-ops and the skill behaves exactly as documented in the rest of `SKILL.md`. `/dev-framework-rl` is the only caller that triggers per-stage mode.

## Sub-commands and helpers

### `/dev-framework status` — compact current-position readout

```powershell
powershell -File C:/Users/skf_s/.claude/skills/dev-framework/scripts/status.ps1
```

Prints: phase, detected types, sensitivity flags, branch, artifact completeness, next gate.

### `phase-capture` — auto-fire hippo capture on phase transitions

Runs the scanner, compares phase against last-recorded for this project, fires `hippo capture` if changed. Designed to run on Stop hook. See `settings.json` hook setup below.

```powershell
powershell -File C:/Users/skf_s/.claude/skills/dev-framework/scripts/phase-capture.ps1
```

State persisted at `~/.claude/dev-framework-state.txt` (one project per line).

### Telemetry — log which gates caught real issues

Log a gate outcome:
```powershell
powershell -File C:/Users/skf_s/.claude/skills/dev-framework/scripts/log-gate.ps1 `
  -Project "C:/Users/skf_s/hippo" `
  -Gate "/cso" `
  -Phase "REVIEW" `
  -Outcome "caught" `
  -Notes "found XSS in markdown render"
```

Outcomes: `passed` | `caught` (gate earned its keep) | `failed` (blocked progression) | `skipped`

Report aggregated insights:
```powershell
powershell -File C:/Users/skf_s/.claude/skills/dev-framework/scripts/telemetry-report.ps1 -Days 30
# Optional: -Project <substring> to filter
```

Surfaces:
- Gate-outcome totals (which gates run, which catch)
- Recent gates that caught real issues
- Recent gates that were skipped
- Per-project insights ("you've never used `/cso` but caught 3 auth bugs at review" pattern)

### Settings.json hook setup (optional, manual — see below)

To auto-fire `phase-capture` on every Stop event, add the hook config shown by:
```powershell
Get-Content C:/Users/skf_s/.claude/skills/dev-framework/HOOK-SETUP.md
```

## Files in this skill

- `SKILL.md` — this entry point
- `PIPELINE.md` — full 9-stage definitions with entry/exit criteria and hippo hooks
- `OVERLAYS.md` — project-type detection table and routing
- `ENFORCEMENT.md` — anti-erosion rules, critical gates, failure recovery loops, stakes/reversibility routers
- `CHECKLIST.md` — 1-page human-readable reference card
- `HOOK-SETUP.md` — proposed settings.json hook for phase-capture (manual install)
- `scripts/scan-project.ps1` — Windows project scanner (deps-based, no false-positive text matching)
- `scripts/scan-project.sh` — Bash project scanner
- `scripts/artifact-check.ps1` — Documentation artifact verifier
- `scripts/status.ps1` — Compact one-liner status (used by `/dev-framework status`)
- `scripts/phase-capture.ps1` — Auto hippo capture on phase transitions (hook target)
- `scripts/log-gate.ps1` — Append-only telemetry log
- `scripts/telemetry-report.ps1` — Aggregate telemetry insights
- `overlays/{ui,ai-agent,backend,quant,cli,library,mobile}.md` — per-type gate overlays
- `logs/telemetry.jsonl` — append-only gate-outcome log (created on first `log-gate` call)

## Quick chain reference

```
1. DISCOVER   /office-hours | /search-first | /brainstorming | /plan-ceo-review
2. SCAFFOLD   /project-scaffold  + /design-consultation (UI)
3. PLAN       /writing-plans → /plan-eng-review + /plan-design-review (UI) → /codex (plan)
4. EXECUTE    /full-power | TDD/EDD | framing pass on fix-it sub-tasks
5. VERIFY     /verify | /qa | /smoke-test | /run            ← RUNTIME EVIDENCE REQUIRED
6. REVIEW     /self-review → /review → /codex (diff) → /cso (sensitive) → /design-review (UI)
7. SHIP       /ship-check → /sinking-ship → /commit or /ship → /publish-repo (library)
8. DEPLOY     /land-and-deploy → /canary → Lighthouse (frontend)
9. LEARN      /document-release → /retro → hippo outcome --good + hippo capture
```

## One rule above all

**Speed directives do not skip gates.** If you're tempted to skip VERIFY, REVIEW, or DEPLOY under deadline pressure — that IS the failure mode the framework exists to prevent.
