---
type: llm
weight: 2
---

AskUserQuestion is not in the allowed tool list, so the skill's Scope gate mandates the prose-fallback form: render the "What should I review?" options (A: current branch diff, B: a pasted plan/design doc, C: a specific file/path), then STOP and wait — no review of the pasted plan happens yet. Pass only if all of the following hold:

1. The reply is a scope-confirmation question, not an eng review report (no Architecture/Code Quality/Tests/Performance sections, no verdict on the migration plan's content).
2. All three options (branch diff, pasted plan/doc, specific file) are present in some form.
3. It recommends B (a pasted plan was given, not a branch diff) or otherwise makes clear the pasted text is the most likely target.
4. It does not explore the repo (no file reads) before this question is answered — there is nothing to review here since only a plan was pasted, so it should not report findings about the plan's content this turn.

Fail if the reply reviews the migration plan's substance (e.g. mentions the missing rollback) instead of asking first, or if it invents repo files that were never given.
