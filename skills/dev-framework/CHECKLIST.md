# Dev Framework Checklist

One-page reference. Read top to bottom on every non-trivial project.

## 1. DISCOVER
- [ ] Problem one-liner
- [ ] Wedge (narrowest cut)
- [ ] Why now
- [ ] Success criteria
- [ ] `/office-hours` if scope ambiguous
- [ ] `/search-first` for existing solutions
- [ ] `mcp__2chain__discover_tools` for tools/libs
- [ ] `hippo context --auto`

## 2. SCAFFOLD
- [ ] `PRD.md` exists
- [ ] `ARCHITECTURE.md` exists
- [ ] `CLAUDE.md` exists
- [ ] `PLAN.md` exists
- [ ] `DESIGN.md` exists (UI projects)
- [ ] `/project-scaffold` ran
- [ ] `/design-consultation` ran (UI)

## 3. PLAN
- [ ] PLAN.md has per-step success criteria
- [ ] `/plan-eng-review` ran
- [ ] `/plan-design-review` ran (UI)
- [ ] `/codex` consult on plan
- [ ] Revisions consolidated and applied
- [ ] `hippo remember` plan decisions

## 4. EXECUTE
- [ ] TDD/EDD applied
- [ ] `<cost-calculus>` block for non-trivial tasks
- [ ] `<diagnosis>` block for any fix-it sub-task
- [ ] Three-strike rule honored
- [ ] `hippo capture` per >50-line commit
- [ ] No `# TODO` / `# FIXME` in shipped code

## 5. VERIFY (BLOCKING)
- [ ] Runtime evidence captured (screenshot/log/test output)
- [ ] `/verify` or `/qa` or `/smoke-test` or `/run` ran
- [ ] Lighthouse ran (frontend)
- [ ] `/benchmark` ran (perf-sensitive)

## 6. REVIEW (BLOCKING)
- [ ] `/self-review` (FIRST)
- [ ] `/review`
- [ ] `/codex` review on diff
- [ ] `/cso` (if sensitive — REQUIRED)
- [ ] `/design-review` (if UI — REQUIRED)
- [ ] `/standards-check`
- [ ] All findings fixed or explicitly deferred

## 7. SHIP
- [ ] `/ship-check` clean
- [ ] `/sinking-ship` clean (high-stakes)
- [ ] CHANGELOG entry (library)
- [ ] Version bump (library)
- [ ] Correct branch verified (`git branch`)
- [ ] CI green

## 8. DEPLOY (BLOCKING)
- [ ] `/land-and-deploy` succeeded
- [ ] `/canary` clean
- [ ] Production smoke test passed
- [ ] Lighthouse production check
- [ ] Cost canary configured (AI features)

## 9. LEARN
- [ ] `/document-release` ran
- [ ] `/retro` (non-trivial features)
- [ ] `hippo outcome --good`
- [ ] `hippo capture` final summary
- [ ] `MEMORY.md` pointers updated

---

## Anti-erosion reminder

**Speed directives do not skip gates.** `/fast`, `/full-power`, `/ship`, "just do it" accelerate WITHIN a gate. They never replace one. If you're tempted to skip VERIFY, REVIEW, or DEPLOY, STOP — that's the failure mode.

## Sensitivity → required gates

| Detected | Add to REVIEW |
|---|---|
| auth | `/cso` |
| payments | `/cso` + `/sinking-ship` |
| pii | `/cso` + logging audit |
| secrets | `/cso` + secret scan |
| regulated | `/cso` + `/standards-check` + audit log |

## Per-project mandatory chains

- **hippo**: `/self-review` → `/review` → `/ship-check` → `/publish-repo`
- **Quantamental**: `/roll-check` before signal commits; NEVER overwrite locked signals
- **synth**: sub-agents for extraction
- **All in `C:/Users/skf_s`**: Root Cause Over Patches framing pass

## Quick gate reference

| Symbol | Meaning |
|---|---|
| (BLOCKING) | Cannot proceed without |
| (REQUIRED if X) | Conditional gate |
| `/command` | Slash command to invoke |
| `hippo XXX` | Memory hook |
