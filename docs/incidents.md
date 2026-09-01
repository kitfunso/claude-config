# Incident & measurement archive

Stories evicted from the always-loaded rules. This file is never injected; rules
point here with one-liners. Append new entries at the top; do not rewrite history.

## 2026-09-01 — rulebook restructure (this file created)

The global CLAUDE.md's numbered "Priority Order" families and the per-hook
biography paragraphs were collapsed into the Precedence block and the Hooks table
(via /improve-docs-architecture). History that lived in the deleted block:

- The families ran 1–8: CRITICAL/user overrides, Root Cause Over Patches,
  Lazy-Smart, Verification, Karpathy framing, Decisiveness, Token Discipline,
  Stop Slop.
- "Done means done" was folded into Honest Reporting; "Act. Don't ask" and
  "A question is a question" into Decisiveness; "Speed" into Token Discipline;
  "Short responses" into the STE-100 section (added 2026-08-14, folded
  2026-09-01).
- The project CLAUDE.md at the user root carried second, drifting copies of
  Decisiveness / Token Discipline / Stop Slop until 2026-09-01; its two
  ASK-FIRST lists had diverged. The dedupe merge fixed that.
- Hook prose named the home box's `.js` files while this box runs Python ports —
  a machine fact asserted in a shared doc. The Hooks table now binds by rule
  name, with `settings.json` as the per-box registry.

## Comment budget (rules/coding-standards.md)

Incident: aura `src/decide.js` — 53 comment lines out of 106; a one-line change
carried a 12-line comment block. Led to the comment-budget hook.

## PS 5.1 stderr redirect (Shell Discipline)

21 measured incidents of `2>&1` on native exes (git/gh/node) wrapping stderr in
NativeCommandError and faking failure (Mirror data, 2026-07-18). Led to the
PS-stderr hook.

## Capability existence (global CLAUDE.md)

Incident 2026-06-16: claimed `/project-scaffold` didn't exist — it did — then
substituted a self-authored plan. Two failures stacked: asserted absence without
checking, plus silent pivot. (The one-line rule and the story both remain in the
rule section; recorded here so the story can be trimmed there later if chosen.)
