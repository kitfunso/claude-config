# HTML-First Outputs: patterns and worked examples

Reached from the HTML-First Outputs rule in the global CLAUDE.md. Read it once you
have decided the deliverable is an HTML page and you are choosing its shape.

Reference: claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html
and thariqs.github.io/html-effectiveness (20 worked examples).

## What each deliverable wants

- **A report**: quant validation/backtest reports, audits, weekly status, incident
  postmortems. Sortable tables, red/green deltas, collapsible sections, charts.
- **A plan or spec for review**: milestones, inline SVG data-flow diagrams, risk
  tables, side-by-side option trade-offs.
- **Code review or code understanding**: annotated diffs with severity tags, module
  maps with the execution path highlighted.
- **Design exploration**: 2 to 4 visual directions in a grid to pick from (pairs with
  the lock-taste-first rule), design-token sheets, component variant sheets.
- **A prototype**: clickable multi-screen flow, or a parameter sandbox with sliders,
  built before the real thing.
- **Research or learning**: explainers with collapsible steps and live demos.
- **A one-off editing UI**: a purpose-built interface for one dataset (triage board,
  flag editor, prompt tuner).
- **A small web product, demo, or dashboard** (hackathons, internal tools): static
  single file plus flat JSON data. Deploys to Vercel or Pages in seconds, and a full
  redesign is one Write pass (HarnessArena, 2026-06-12).
- **A demo video**: page-injected caption and intro overlay hooks, a scripted
  Playwright recording, then ffmpeg (template: harness-arena/video/record.mjs).

## Techniques that make it land

Tabs and accordions instead of long scrolls. Inline SVG instead of ASCII art. "Copy
as Markdown / JSON / prompt" buttons, so results flow back into the loop. Sliders and
knobs for anything tunable. Data loaded by fetch of flat JSON. Open the file in the
browser when you are done.
