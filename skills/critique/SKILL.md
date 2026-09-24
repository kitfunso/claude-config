---
name: critique
description: Brutal-honesty critique of a piece of work (code, a plan, a design, a doc, a decision memo), findings ranked by severity with cited evidence and a concrete fix each. Use when the user asks to critique something, tear it apart, poke holes in it, or be brutally honest about it, including before they ship, run, send, or merge it.
---

Be brutally honest and critique the work. Identify weaknesses, gaps, and flawed assumptions. Then offer concrete suggestions for improvements and enhancements. Do not sugarcoat: directness is valued over diplomacy.

## Method

- Read every artifact under critique in full before writing a word. No critique from memory or from a summary.
- Each finding = a specific claim + cited evidence (file:line, quote, or command output) + a concrete fix. A weakness you cannot cite is a hypothesis: label it as one. Pasted text has no file:line, so quote it. Minor findings meet the same bar or get cut.
- Rank findings by severity, worst first, and keep any severity labels in that same order. Lead with what would actually hurt.
- Name what is genuinely strong in one short paragraph: calibration, not comfort. Skip it if nothing earns it. Never credit something a finding criticises.
- End with the single change that matters most, as the last line. Questions for the user go before it.

$ARGUMENTS