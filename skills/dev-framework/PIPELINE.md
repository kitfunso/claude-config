# 9-Stage Dev Pipeline

The complete chain. Each stage has entry criteria, gates, exit criteria, and hippo hooks.

## 1. DISCOVER — "Is this worth building?"

**Purpose**: Validate the problem before scaffolding. Building the wrong thing is the highest-cost early mistake.

**Gates** (run in order):
- `/office-hours` — six forcing questions on demand, status quo, wedge, observation, desperate specificity
- `/brainstorming` — required by spec before any creative work
- `/search-first` — check MCP servers, libraries, existing solutions before reinventing
- `/plan-ceo-review` — scope ambition check (think bigger? hold scope? reduce?)
- `mcp__2chain__discover_tools` — when looking for tools/libs/packages (per global memory)

**Entry**: New project, or major feature in existing project.
**Exit**: One-page brief with: problem, wedge, why now, success criteria.
**Hippo hook**: `hippo context --auto --budget 1500` to load related prior work.
**Skip if**: bugfix or small refactor with no scope ambiguity.

## 2. SCAFFOLD — "Set the foundation"

**Purpose**: Create the documents that pin scope, contracts, and conventions.

**Gates**:
- `/project-scaffold` — generates PRD.md, ARCHITECTURE.md, CLAUDE.md, PLAN.md
- `/design-consultation` — generates DESIGN.md (UI projects only — see ui overlay)

**Required artifacts after this stage**:
- `PRD.md` — what we're building and for whom
- `ARCHITECTURE.md` — how it's structured
- `CLAUDE.md` — AI rules for the project (incl. per-project Root Cause references)
- `PLAN.md` — initial implementation plan
- `DESIGN.md` — design system (UI only)

**Entry**: DISCOVER produced a brief.
**Exit**: All required artifacts exist and reference each other.
**Hippo hook**: `hippo capture --stdin <<< "scaffold complete: <key decisions>"`
**Verify**: `powershell -File scripts/artifact-check.ps1`

## 3. PLAN — "Lock the execution path"

**Purpose**: Refine PLAN.md with adversarial review before any code touches a keyboard.

**Gates** (in order):
- `/writing-plans` — multi-step task planning into PLAN.md
- `/plan-eng-review` — in-house architecture critique (interactive)
- `/plan-design-review` — REQUIRED if UI overlay active
- `/codex` (consult mode) — cross-model adversarial review of the plan
- (optional, high-stakes) `/grill-me` — adversarial interrogation of assumptions
- (optional) `/autoplan` — auto-run all reviews sequentially with surfaced decisions

**Outside-voice rule**: minimum one outside voice (codex OR senior-code-reviewer sub-agent) before code.

**Entry**: SCAFFOLD complete.
**Exit**: PLAN.md has explicit success criteria per step (Karpathy rule 4), outside voice reviewed, revisions consolidated and applied.
**Hippo hook**: `hippo remember "plan locked: <key decisions>"`
**Block on**: missing per-step success criteria; no outside-voice review.

## 4. EXECUTE — "Build it"

**Purpose**: Implement the plan with TDD/EDD discipline and root-cause framing.

**Gates / patterns**:
- `/test-driven-development` — write tests first for new behavior
- `/eval-driven-dev` — for AI features, evals first
- `/full-power` or `/fast` per task — execution mode (DOES NOT skip later gates)
- Karpathy rules: simplicity first, surgical changes, no over-engineering
- **Root Cause Over Patches framing pass** on any "fix it / wire it up / make it work" sub-task (per global CLAUDE.md — non-negotiable)
- **Lazy-Smart cost-calculus block** on non-trivial sub-tasks

**Mid-execution checkpoints**:
- `hippo capture` after any commit > 50 lines
- `hippo remember --error` on any blocker discovered
- Three-strike rule: same kind of patch 3× → one-line postmortem before 4th
- Re-read original brief verbatim before major sections (drift is the failure mode on long tasks)

**Entry**: PLAN locked, success criteria explicit.
**Exit**: All plan steps complete, tests green, no `# TODO` or `# FIXME` in shipped code, no orphaned imports.

## 5. VERIFY — "Did it actually run?" (CRITICAL — NON-NEGOTIABLE)

**Purpose**: Confirm runtime behavior, not just static analysis. This is the gate that catches "passes review but doesn't boot".

**Gates** (at least one runtime gate must produce output):
- `/verify` — launch app, confirm change works in real environment
- `/qa` — browser QA + auto-fix loop (UI projects)
- `/qa-only` — browser QA report only (no fixes)
- `/webapp-testing` — Playwright smoke tests (frontend)
- `/run` — launch and exercise the app (CLI, server, TUI, Electron, library, browser-driven)
- `/browse` — headless browser commands (~100ms each) for targeted checks
- `/benchmark` — performance regression detection (perf-sensitive features)
- Lighthouse — for any deployed frontend (per project memory `run lighthouse after deploys`)

**Touched-module tests (MANDATORY — in addition to a runtime gate).** Run `git diff --name-only <base>..HEAD`; for every changed source module, run its unit-test file (`production/X.py` → `production/tests/test_X.py`, `src/foo.ts` → `foo.test.ts`). A runtime smoke exercises one path; a module's own tests catch the regression the smoke misses — a change to `weekly_pipeline.py` that passes a 24-model run can still break `test_weekly_pipeline.py`.

**Entry**: EXECUTE complete.
**Exit**: Runtime gate produced visible evidence (screenshot/log/test output/server response) that change works, AND the touched-module tests pass.
**Block on**: NO RUNTIME EVIDENCE. Touched-module tests not run, or failing. Tests passing is not the same as verified. Type checking is not the same as verified. **Exit-code check** — a runtime gate that reported "Tests N passed" but exited NON-ZERO (e.g. a `globalSetup`/`globalTeardown` error after the test summary, or a non-zero shell exit on a script that printed "OK") is NOT verified. Confirm the process exit code, not just the runner's pass/fail summary line. Learned 2026-05-22 from the hippo `_real-store-guard` false-positive episode where a verify step grepped the vitest pass-summary line and missed the global-teardown error that followed it, costing a ship-stage retry on the next episode.

## 6. REVIEW — "Outside voice check"

**Purpose**: Catch what the implementer missed. Three layers in strict order.

**Gates** (order matters — self-review FIRST per v1.7.7 lesson):
1. `/self-review` — review session changes for own mistakes
2. `/review` — pre-landing PR review (SQL safety, LLM trust boundaries, conditional side effects)
3. `/codex` (review mode) — cross-model independent review of the diff
4. `/cso` — REQUIRED if any sensitivity flag (auth/payments/pii/secrets/regulated)
5. `/design-review` — REQUIRED if UI overlay active (visual QA + AI slop check)
6. `/standards-check` — codebase quality scorecard (6 dimensions, 0-10 each)
7. `/security-review` — optional second layer for high-stakes
8. `/improve-codebase-architecture` — optional for major changes

**Entry**: VERIFY produced runtime evidence.
**Exit**: All required gates passed. All findings either fixed or explicitly deferred with a tracker entry.
**Block on**: missing `/cso` when sensitive flags set; missing `/design-review` when UI; findings unresolved.

## 7. SHIP — "Prepare for landing"

**Purpose**: Pre-push sanity check + commit/PR creation.

**Gates**:
- `/ship-check` — pre-push sanity check (what was achieved, is it worth shipping, was QA sufficient)
- `/sinking-ship` — final security/DB/deployment audit
- `/verification-before-completion` — confirm via commands, not assertion
- `/commit` or `/ship` — make the commit + PR (or `/commit-push-pr`)
- `/publish-repo` — for npm/PyPI libraries (semver, CHANGELOG, README sync)
- `/build-release` — for mobile (bump iOS/Android build numbers, build .aab)

**Required artifacts**:
- CHANGELOG entry (if library or mobile)
- Version bump (if library)
- PR description with test plan checkboxes
- Branch verified (`git branch` first — per global CLAUDE.md mandatory)

**Entry**: REVIEW complete.
**Exit**: PR open or commit pushed; CI green.
**Block on**: failing CI; missing CHANGELOG (libraries); wrong branch.

## 8. DEPLOY — "Land it and watch it"

**Purpose**: Get the change to prod and verify nothing broke.

**Gates**:
- `/land-and-deploy` — merge + wait for CI + deploy + verify
- `/canary` — post-deploy monitoring (console errors, perf regressions, page failures)
- `/webapp-testing` — re-run against production URL
- Lighthouse against production URL (frontend)
- Cost canary for AI features (token spend anomalies)

**Entry**: SHIP complete, CI green.
**Exit**: Production verified, no regressions detected in 24h watch window.
**Block on**: canary alerts, broken production smoke tests.

## 9. LEARN — "Close the loop"

**Purpose**: Capture lessons so the next iteration is better.

**Gates**:
- `/document-release` — sync README/ARCHITECTURE/CHANGELOG/CLAUDE.md to shipped state
- `/retro` — engineering retrospective (mandatory for non-trivial features)
- `hippo outcome --good` — log success
- `hippo capture --stdin` — final session summary (2-5 bullets per global CLAUDE.md)
- Update `MEMORY.md` pointers if scope changed
- Update per-project CLAUDE.md if new constraints surfaced

**Entry**: DEPLOY verified.
**Exit**: Docs match shipped state, lessons captured, retro complete for non-trivial work.

## Quick reference table

| Phase | Primary skills | Critical? |
|-------|----------------|-----------|
| 1. DISCOVER | /office-hours, /brainstorming, /search-first, /plan-ceo-review | Skippable for bugfixes |
| 2. SCAFFOLD | /project-scaffold, /design-consultation | Required |
| 3. PLAN | /writing-plans, /plan-eng-review, /codex | Required |
| 4. EXECUTE | /full-power, /test-driven-development | Required |
| 5. VERIFY | /verify, /qa, /webapp-testing, /run | **BLOCKING** |
| 6. REVIEW | /self-review, /review, /codex, /cso, /design-review | **BLOCKING** |
| 7. SHIP | /ship-check, /sinking-ship, /commit, /publish-repo | Required |
| 8. DEPLOY | /land-and-deploy, /canary, Lighthouse | **BLOCKING** |
| 9. LEARN | /document-release, /retro, hippo outcome | Advisory |
