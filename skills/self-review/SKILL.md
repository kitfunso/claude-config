---
name: self-review
description: Review all changes made this session for mistakes, missed requirements, and regressions. Use to review changes or verify correctness.
---

# Self-Review

Review every change made in this session. Be thorough and honest — the goal is to catch mistakes before the user has to.

## Steps

1. **Collect the diff — all three layers**: Resolve the session base first: the branch fork point (`git merge-base HEAD <default-branch>`), or on the default branch, the commit before this session's first commit. Then review `git diff <base>...HEAD` (committed work), `git diff --staged`, and `git diff` (unstaged). Committed work counts — a clean worktree does NOT mean nothing changed this session. If files were newly created, read them in full.

2. **Check each changed file** against these criteria:
   - **Correctness**: Does the logic do what was intended? Off-by-one errors, wrong variable, inverted condition, missing edge case?
   - **Completeness**: Re-read the user's original request verbatim first. Were all requested changes made? Any files or locations missed?
   - **Consistency**: Do new patterns match the existing codebase style? Naming, imports, error handling?
   - **Regressions**: Could any change break existing functionality? Check callers/consumers of modified functions.
   - **Residual debug code**: Any leftover `print()`, `console.log()`, `TODO`, or commented-out code that shouldn't ship?
   - **Security**: Any hardcoded secrets, unsanitized input, or SQL injection vectors introduced?
   - **Types & signatures**: Do function signatures, return types, and type annotations match usage?

3. **Report findings** in this format:
   - If clean: "All changes reviewed — no issues found." (one line, done)
   - If issues found: list each with file, line, what's wrong, and the fix. Then apply the fixes immediately.

## Rules

- Review ALL changed files, not just the last one touched.
- Do not add unrelated improvements, refactors, or style changes — only fix actual mistakes.
- If uncertain whether something is a bug, flag it to the user rather than silently changing it.
- Run any relevant tests or validation scripts after applying fixes.
