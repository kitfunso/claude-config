---
description: Run the canonical frontend build pipeline — lock taste via DESIGN.md, implement with /frontend-design, QA with /design-review
argument-hint: [what to build, e.g. "landing page for hippo"]
---

You are running the canonical frontend build pipeline. The user wants: $ARGUMENTS

Follow these stages in order. Skip stages only if the trigger condition fails. Confirm direction with the user once at the end of Stage 1, then commit and execute.

## Stage 0 — Scope check (silent)

Decide build size and skip rules:
- Trivial edit (one selector, copy change, single component tweak): tell the user this doesn't need the pipeline, just do it directly. Stop.
- Single new component with existing DESIGN.md at project root: skip Stage 1, jump to Stage 3.
- New page or section: do Stages 1, 3, 6.
- New project from scratch or major redesign: do all stages.

Check for existing `DESIGN.md` at project root. If present, read it and skip Stage 1 unless the user wants to redesign.

## Stage 1 — Lock taste

Pick the lightest combo that locks an aesthetic direction. Present the user with one preferred path, not a menu.

Options ranked by use case:
- No reference, want exploration: `/design-shotgun` — generates 3-5 visual variants, opens comparison board.
- Want to clone or remix a real brand: pull a starter from https://github.com/VoltAgent/awesome-design-md (69+ DESIGN.md files for Linear/Vercel/Stripe/etc.) and adapt.
- Want a live generator: AIDesigner MCP (paid) — `generate_design`, `refine_design`, URL inspire/clone/enhance modes. Generate 2-4 candidates, pick one.
- Want a guided interview: `/design-consultation`.

Output of this stage: a committed `DESIGN.md` at project root using the spec from https://github.com/google-labs-code/design.md (YAML front matter for tokens + markdown rationale). This is the single source of truth for the rest of the build.

Pause here. Show the user the locked DESIGN.md and confirm the direction before implementing.

## Stage 2 — Plan-review (only if build is >3 steps)

Run `/plan-design-review` on the implementation plan to catch holes before coding.

## Stage 3 — Implement against the locked taste

Use `/frontend-design` as the implementation entry point — it forces a bold aesthetic direction and bans AI-slop defaults (Inter/Roboto/Arial, purple gradients on white, predictable layouts). Reference the DESIGN.md tokens directly.

Companion skills to use as needed:
- `/design-html` — production HTML/CSS finalizer for static pages.
- `/artifacts-builder` or `/web-artifacts-builder` — multi-component React + Tailwind + shadcn for elaborate artifacts.
- `/theme-factory` — apply one of 10 preset themes if no custom palette is needed.

Implement section by section against the DESIGN.md, not in one big dump.

## Stage 4 — Component sources (steal, don't reinvent)

When you need a component pattern, pull from these instead of writing from scratch:
- shadcn/ui + tweakcn.com (visual theme builder, exports Tailwind tokens that match DESIGN.md)
- magicui.design and ui.aceternity.com (animated Tailwind components)
- 21st.dev (community shadcn marketplace, search by pattern)
- originui.com, kokonutui.com (free shadcn variants)

## Stage 5 — Pattern research (only when stuck on a flow)

For non-obvious flows (onboarding, checkout, dashboard layouts):
- mobbin.com — real product UI screenshots indexed by pattern
- pageflows.com — full user flows from real products
- godly.website, landings.dev — landing-page galleries (feed promising URLs into AIDesigner clone mode)

## Stage 6 — QA

- `/design-review` — visual QA audit with iterative fixes
- `/qa` — browser QA test + auto-fix loop
- After deploy: run lighthouse (per existing rule)

## Reporting

End-of-pipeline summary in 2-3 lines: what shipped, what stage was skipped and why, what's next. No long retrospectives.
