# Incident & measurement archive

Stories evicted from the always-loaded rules. This file is never injected; rules
point here with one-liners. Append new entries at the top; do not rewrite history.

## Rule edit history

Stamps stripped from rule headings on 2026-09-04, so the changelog stops riding in
every turn's context. As they stood:

- Delegating to sub-agents: "tightened for Opus 5" (section folded into Sub-agents).
- Speed: "Opus 5 and Fable 5 sessions, user directive 2026-08-14" (section deleted;
  its one live clause folded into Sub-agents).
- Lazy-Smart mandatory output artifact: "tightened 2026-06-10" (section merged into
  Root Cause Over Patches, one `<diagnosis>` block).
- Verification mandatory output artifact: "provenance-scoped 2026-07-03"; "What this
  rule does NOT authorise": "scoped 2026-07-26" (both merged into Sourcing).
- Rulebook Discipline: "added 2026-07-04, restored 2026-08-14".
- Banned AI-isms: "user directive 2026-07-17" on the "canonical" ban.
- STE-100 Response Style: "user directive 2026-07-29"; its short-responses addendum:
  "user directive 2026-08-14" (both merged into Output prose).
- Subagent model routing: "added 2026-07-02, re-based on roles 2026-07-26".
- Shell Discipline: "measured via Mirror, 2026-07-18".
- Comments (rules/coding-standards.md): "Keith 2026-08-30, all projects".
- Dependencies & Compatibility (rules/coding-standards.md): "probation, added
  2026-07-31, no incident yet".

## No Fabrication (global CLAUDE.md, now the Sourcing section)

Incident 2026-06-24 (quanthack): asserted "the 30-strat book = the 29-strat book plus
one sleeve" from inference instead of reading `final_universe.json.bak-prefinal`, then
computed and presented a full performance-metrics table on that fabricated book as if
real. The actual 30-book differed by 5 sleeves; hours of comparison were built on a
membership never read from disk. Root cause: stated a set's contents from memory
instead of reading the file. The rule exists because that broke user trust.

## Shell discipline measurements (Mirror, 2026-07-18)

`cd X; cmd` compounds were 61% of measured PowerShell errors, and `cd` was the number
one shell command at 6,349 calls. Detail: memory files
`feedback_shell_absolute_paths_over_cd.md` and
`feedback_ps51_no_native_stderr_redirect.md`; refresh the data with
`python ~/.claude/mirror/mirror.py` where Mirror is installed.

## Banned AI-isms provenance

The core of the list (delve, underscore, showcase, pivotal, intricate, meticulous,
realm, boast, enhance, notably, surpass, garner, strategically) is corpus-backed:
post-ChatGPT "excess vocabulary" studies of PubMed abstracts (Science Advances 2025,
adt3813) and an FSU follow-up finding spillover into spoken language. The rest
("canonical", leverage, seamless, tapestry, and the others) is house style.

## Rule provenance

- rules/karpathy-guidelines.md is adapted from
  https://github.com/forrestchang/andrej-karpathy-skills.
- The Simplicity First ladder and the `SHORTCUT:` comment convention come from
  github.com/dietrichgebert/ponytail, adopted 2026-09-01, with ladder rung 3
  rewritten to defer to project law.
- Rulebook Discipline came from ARC Prize harness notes (cheap generator, hard
  verifier, measurement-fed refinement): `clawd/memory/arc-harness-notes.md` on the
  home box. The ARChitects scored 72.5% on ARC-AGI-1 and 2.5% on ARC-AGI-2, the
  single-benchmark risk the probation tag guards against.

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
checking, plus silent pivot. (The story was trimmed from the rule section on
2026-09-04; the one-line rule stays there and this file holds the story.)
