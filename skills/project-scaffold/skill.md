---
name: project-scaffold
description: Generate PRD, Architecture, CLAUDE.md, and Plan docs when starting a new project from scratch.
---

# Project Scaffold

Generate four foundation documents that turn AI-assisted development into structured engineering. Each document has a specific job. Together they prevent scope creep, spaghetti code, quality drift, and getting lost in complexity.

**Announce at start:** "I'm using the project-scaffold skill to generate the four foundation documents."

## The Four Documents

### 1. PRD (Product Requirements Document)

**File:** `docs/PRD.md`

**Purpose:** Define what the app IS and what it IS NOT. This is the scope guard. Without it, every session drifts into "wouldn't it be cool if..." territory.

Template: see [`references/prd-template.md`](references/prd-template.md).

**Rules:**
- The "IS NOT" section must have at least 5 items
- Every feature in "Core Features" must map to a problem in "Problem Statement"
- No feature gets added without updating this document first

### 2. Architecture Document

**File:** `docs/ARCHITECTURE.md`

**Purpose:** Tell the AI exactly how to organize folders, data, and services. This prevents spaghetti code and ensures consistency across sessions.

Template: see [`references/architecture-template.md`](references/architecture-template.md).

**Rules:**
- Every directory in the repo structure must have a one-line comment
- The data model must include indexes and constraints, not just columns
- API design must show auth model (who can call what)
- No new service/module gets created without updating this document first

### 3. AI Rules Document (CLAUDE.md)

**File:** `CLAUDE.md` (project root)

**Purpose:** Non-negotiable rules for any AI session working on this project. Quality control. Coding standards. Safety rails. Things that should never be violated regardless of what the prompt says.

Template: see [`references/claude-md-template.md`](references/claude-md-template.md).

**Rules:**
- Keep under 100 lines. Long CLAUDE.md files get skimmed, short ones get read.
- Every rule must explain WHY, not just WHAT
- "Non-Negotiable Rules" section must exist and must be honored by all sessions
- Update this document when a new gotcha is discovered

### 4. Plan Document

**File:** `docs/plans/YYYY-MM-DD-[feature-name].md`

**Purpose:** Step-by-step roadmap. Work on one step at a time. Don't move to the next until the current one is complete and verified. This prevents getting lost in complexity.

Template: see [`references/plan-template.md`](references/plan-template.md).

**Rules:**
- Each step must be independently verifiable (test, build, or visual check)
- Each step must end with a commit
- Never skip ahead. Complete and verify before moving on.
- If a step reveals the plan is wrong, update the plan document first, then continue
- Steps should be 5-30 minutes of work each. Smaller is better.

## When to Use / When NOT to Use

**USE for:**
- New projects, repos, or major initiatives starting from scratch
- Major pivots that fundamentally change what a project does
- When the user says "scaffold", "new project", "kickoff", "project init", "set up a new project"

**DO NOT USE for:**
- Single features (use `/writing-plans` instead)
- Bugfixes (use `/systematic-debugging`)
- Small changes to existing projects
- Research or exploration tasks

## Workflow

When the user invokes `/project-scaffold`:

### Phase 1: Discovery (ask before generating)

1. **Ask up to 4 questions** (use AskUserQuestion):
   - What are you building? (one sentence)
   - Who is it for? (target user + their technical level)
   - What's the tech stack preference? (or "recommend")
   - What are the hard constraints? (budget, timeline, team size, regulatory)

2. **If the user has an existing codebase**, explore it first:
   - Read any existing CLAUDE.md, README, package.json, pyproject.toml
   - Understand patterns they're comfortable with
   - Note reusable code, libraries, and conventions

### Phase 2: PRD First (sequential with review gate)

3. **Generate the PRD only.** Write to `docs/PRD.md`.
4. **Present the PRD to the user.** Specifically highlight:
   - The "IS NOT" list (ask: "Does this capture what's out of scope?")
   - Success metrics (ask: "Are these realistic?")
   - Pricing model (ask: "Does this pricing make sense?")
5. **Wait for user approval or feedback.** Revise the PRD if needed.

### Phase 3: Architecture + CLAUDE.md (after PRD approved)

6. **Generate Architecture doc** (`docs/ARCHITECTURE.md`) based on the approved PRD.
7. **Generate CLAUDE.md** (project root) with non-negotiables derived from PRD constraints.
8. **Present both.** Highlight key decisions: tech stack, data model, service boundaries.
9. **Wait for user approval.** This is the last chance to change architecture before planning.

### Phase 4: Plan (after Architecture approved)

10. **Generate ONLY the first phase/month plan** (`docs/plans/YYYY-MM-DD-phase-1.md`).
    - NOT the full 6-month plan. Just the first executable chunk.
    - Each step must be independently verifiable.
    - Last step: "Generate Phase 2 plan."
11. **Present summary table:**

```
| Document | File | Status |
|----------|------|--------|
| PRD | docs/PRD.md | Approved |
| Architecture | docs/ARCHITECTURE.md | Approved |
| AI Rules | CLAUDE.md | Approved |
| Phase 1 Plan | docs/plans/YYYY-MM-DD-phase-1.md | Ready |
```

12. **Offer next step:** "Ready to start Step 1 of the Phase 1 plan?"

## Updating Documents

These are living documents. When scope changes:
- **New feature request** -> Update PRD first (check "IS NOT" list), then Architecture if needed, then Plan
- **Bug discovered** -> Add to CLAUDE.md "Common Mistakes" section
- **Architecture change** -> Update Architecture doc, then review Plan for impact
- **New non-negotiable** -> Add to CLAUDE.md immediately

## Integration with Other Skills

- After scaffold: use `/writing-plans` for detailed task breakdown within each plan step
- During execution: use `/executing-plans` or subagent-driven-development
- Before claiming done: use `/verification-before-completion`
- After shipping: use `/document-release` to keep docs current
