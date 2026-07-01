# Enforcement Rules

The framework is only as strong as its weakest moment. These rules close the gaps that speed directives, fatigue, or "just one more" thinking open.

## Anti-erosion (CRITICAL)

Speed directives — `/fast`, `/full-power`, `/ship`, "just do it", "do this now", "no need to review" — accelerate execution *within* a gate. They NEVER skip a gate.

**The v1.7.7 incident**: hippo release shipped without `/review` and `/ship-check` under speed pressure. Keith caught it twice in the same release window. Memory entry locked the rule: "No speed directive overrides the chain."

**Implementation**: when entering a phase, the skill lists the gates required and confirms each has produced output. If a gate is missing and a speed directive is active, print:

```
PHASE: <name>
SPEED DIRECTIVE DETECTED: <directive>
GATES REQUIRED: <list>
GATES MISSING: <list>
ACTION: speed directive does not bypass these gates. Run them.
```

## Critical gates (BLOCKING — strict profile)

These gates BLOCK phase progression if missing.

### VERIFY
**Runtime evidence required.** Tests passing alone is NOT sufficient. A `/verify`, `/qa`, `/smoke-test`, or `/run` invocation must have produced visible output (screenshot, log, test run, server response).

### REVIEW
- `/self-review` BEFORE `/review` (order matters per v1.7.7)
- `/cso` REQUIRED if any sensitivity flag (auth/payments/pii/secrets/regulated)
- `/design-review` REQUIRED if UI overlay active
- All findings either fixed or explicitly deferred with a tracker entry

### SHIP
- `/ship-check` output recorded clean
- CHANGELOG entry exists for the change
- Version bumped (libraries)
- Correct branch (`git branch` verified per global CLAUDE.md)

### DEPLOY
- `/land-and-deploy` completed successfully
- `/canary` ran post-deploy with clean result

## Required artifacts (BLOCKING at SCAFFOLD exit)

These must exist before leaving SCAFFOLD phase:

- `PRD.md`
- `ARCHITECTURE.md`
- `CLAUDE.md`
- `PLAN.md`
- `DESIGN.md` (if UI overlay active)

Run `scripts/artifact-check.ps1` to verify.

## Cost-calculus block (REQUIRED for non-trivial tasks)

Per global CLAUDE.md Lazy-Smart rule, any non-trivial task at EXECUTE phase requires a `<cost-calculus>` block before writing code:

```
<cost-calculus>
Patch path A: <one line>
Structural path B: <one line>
Total cost A across N rounds: <estimate>
Total cost B in 1 round: <estimate>
Pick: <A | B with reason>
</cost-calculus>
```

Skipping = automatic Lazy-Smart violation. The block is the proof.

## Framing pass (REQUIRED for fix-it tasks)

Per global CLAUDE.md Root Cause Over Patches rule, any "fix it / make it work / wire it up" sub-task requires a `<diagnosis>` block as the FIRST content of the response:

```
<diagnosis>
Problem: <one sentence, no mention of the fix>
Root cause: <upstream component, contract, or producer>
Proposed fix: <what you intend to change>
At root or downstream? <root | downstream — if downstream, name what's being bypassed>
</diagnosis>
```

If downstream → STOP. Reply with the root-cause reframe and wait for explicit confirmation in a separate user message.

**Patch smells (STOP signals)**: third-party shim around a broken interface, one-time cleanup script, manual data fix, skip-list, repeated guard at N call-sites, "let me try a small thing first."

## Three-strike rule

If the same kind of fix appears 3 times in a session, write a one-line postmortem on WHY before attempting the 4th. Patches accumulate debt — they don't compound into a working system.

## Failure recovery loops

### VERIFY fails (app doesn't run)
1. `/investigate` or `/systematic-debugging` to find root cause
2. Framing pass (`<diagnosis>` block)
3. Fix at root, not symptom
4. Re-run VERIFY

### REVIEW finds issues
1. Sort findings: critical / important / nit
2. Critical + important: `/full-power` (with framing pass) to fix
3. Nits: defer to tracker
4. `/self-review` again
5. `/review` again

### CSO finds vulnerabilities
1. Rotate any exposed secrets IMMEDIATELY
2. Fix at root (input validation, output encoding, etc.)
3. Re-run `/cso`
4. Document the fix in `ARCHITECTURE.md` security section
5. Update CLAUDE.md if it's a class of issue to watch for

### Canary alerts post-deploy
1. Rollback first if user-impacting
2. `/investigate` to find regression
3. Hotfix only if active outage (otherwise revert + re-walk pipeline from REVIEW)
4. Post-incident retro mandatory

## Speed directive interactions

The skill recognizes these and adjusts execution mode WITHIN gates only:

- `/fast` — terser tool use, fewer optional probes, SAME gate set
- `/full-power` — parallel sub-agents, max thoroughness within each gate
- `/ship` — bundles SHIP + DEPLOY phases but doesn't skip earlier phases
- "quick mode" — terse output, NEVER skipped investigation (per `feedback_quick_mode_is_not_no_research`)

NONE of these skip critical gates.

## Stakes router

Detected from PRD.md, project memory, or asked. Adds gate intensity:

| Stakes | Required gates beyond default |
|---|---|
| Toy / learning | DISCOVER + SCAFFOLD + EXECUTE only |
| Side project | + PLAN + VERIFY |
| Production | + REVIEW + SHIP + DEPLOY |
| Paid client | + `/cso` always, audit log |
| Regulated (finance/health/PII at scale) | + `/cso` + `/standards-check` + artifact retention |

## Reversibility router

For irreversible operations (DB migrations, prod deploys, payment integrations, force-pushes to shared branches):

- `/careful` mode active (destructive command warnings)
- `/guard` for edit-scope restriction
- Extra `/codex challenge` adversarial pass before SHIP
- Rollback plan documented in PR

## Branch hygiene (mandatory pre-op)

Per global CLAUDE.md: `git branch` BEFORE any git operation. Multiple sessions may be on different branches. NEVER assume main.

Skill enforces: scan reports `branch`. Phase progression past PLAN requires branch confirmed by user or scan.

## Documentation rewrites

Per global CLAUDE.md: before fully rewriting `~/.claude/*` or any `CLAUDE.md`, show the proposed content and wait for explicit "apply". Save a `.old` backup before overwriting. Targeted Edits proceed normally.

## Telemetry (advisory — track over time)

Over time, log per-project:
- Which gates ran
- Which gates caught real issues (triggered a fix)
- Which gates were skipped (with reason)
- Time per phase

Surface insights at `/retro`: "you've never used `/cso` but last 2 sensitive features had auth bugs at review — add `/cso` earlier".

## When to NOT enforce

Genuine exceptions where critical gates relax:

- **Active outage hotfix** — skip REVIEW but flag root-cause follow-up; full chain on next non-hotfix commit
- **Single bad prod row from already-fixed bug** — manual data fix is fine; one-off, not pattern
- **Toy / learning project** — only DISCOVER + SCAFFOLD + EXECUTE apply (stakes router)
- **Trivial typo / formatting / comment edit** — framing pass and cost-calculus don't fire

Document the exception in the commit message. Don't let it become a pattern.
