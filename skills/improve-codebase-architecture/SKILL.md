---
name: improve-codebase-architecture
description: Audit codebase architecture and propose concrete structural fixes: coupling, cohesion, boundaries, testability.
---

Audit the codebase's **architecture** and propose concrete improvements. This is structural work, not style nitpicking.

## Phase 1: Survey

Map the codebase before critiquing it.

- Entry points and data flow (where do requests/events enter, how do they propagate)
- Module boundaries and their dependencies (who imports whom)
- Layering: is there a clear separation between domain, application, infrastructure?
- State management: where does state live, who mutates it, what's the lifecycle?
- External integrations: databases, APIs, queues, filesystems
- Test structure: unit vs integration vs e2e, what's tested where

Report the map in 5-10 bullet points. If the codebase is huge, pick the subsystem most relevant to the user's request.

## Phase 2: Diagnosis

Check the mapped subsystem against every category below; silence on a category means checked-and-clean, not skipped.

Identify real architectural problems. Focus on these categories:

**Coupling issues**
- Modules that shouldn't know about each other but do
- Circular dependencies
- Shared mutable state across boundaries
- "God objects": one class/module that touches everything

**Cohesion issues**
- Modules that mix unrelated responsibilities
- Business logic leaking into controllers/routes/views
- Infrastructure concerns (DB, HTTP) mixed with domain logic

**Abstraction issues**
- Wrong abstractions: interfaces with one implementation, factories that don't vary, premature generalization
- Missing abstractions: repeated patterns that should be unified
- Leaky abstractions: implementation details bleeding through interfaces

**Boundary issues**
- Missing or porous boundaries between bounded contexts
- Direct DB access from everywhere instead of a repository/service
- Public APIs that expose internal types

**Testability issues**
- Hard-to-test code due to hidden dependencies, global state, or tight coupling to infrastructure
- Tests that know too much about implementation
- No seams to inject fakes or stubs

**Lifecycle / complexity debt**
- Dead code paths
- Feature flags that never shipped or never got cleaned up
- Duplicate implementations of the same thing
- Configuration sprawl

For each issue: **what** is wrong, **where** it lives (file:line), **why** it matters (what it costs the team), and **severity** (critical / high / medium / low).

## Phase 3: Recommendations

Propose changes in order of impact-to-effort ratio. For each:

- **Change:** concrete description (not "improve modularity", but "extract `PricingService` from `OrderController`")
- **Why:** what problem it fixes
- **Blast radius:** how many files/callers change
- **Risk:** what could break, how to mitigate
- **Test strategy:** how you'd verify the refactor didn't regress behavior
- **Scope:** small (1-2 files), medium (single subsystem), large (cross-cutting)

Group into:
- **Do now:** high impact, low risk
- **Plan for next sprint:** high impact, higher risk or effort
- **Don't do:** tempting but not worth it (explain why)

## Phase 4: Execution plan

If the user wants to proceed, pick the top 1-3 changes and outline the step-by-step execution. Prefer:

1. Characterization tests first (lock in current behavior)
2. Incremental refactors with tests passing at each step
3. One PR per logical change, not one mega-PR
4. Reversibility: each step should be independently mergeable and revertible

## Ground rules

- **Respect Chesterton's Fence.** A module that looks "weird" may encode a hidden constraint; ask why it exists before proposing to remove or rewrite it.
- **Aim for a codebase that's easier to change, not a textbook-pure one.**
- **Measure, don't guess.** If you claim something is slow or complex, show the evidence (profiler, cyclomatic complexity, churn data).
- **Justify every abstraction by a need that exists now, not a speculative future one.**

---

Target: $ARGUMENTS

If no target is specified, audit the whole codebase rooted at the current working directory.
