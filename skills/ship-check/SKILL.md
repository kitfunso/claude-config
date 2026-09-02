---
description: Pre-push sanity check — what did we achieve, is it worth shipping, did we do enough QA
---

Run a **ship-check** on the current branch. Answer these four questions honestly, with evidence.

## 1. What exactly have we achieved?

- Resolve the default branch (`git symbolic-ref refs/remotes/origin/HEAD` or `git remote show origin`); call it BASE
- Run `git diff BASE...HEAD --stat` to see all changes
- Run `git log BASE..HEAD --oneline` to list all commits
- Summarize the work in 2-3 bullet points: what changed, what's new, what was fixed
- If there are uncommitted changes, flag them

## 2. Is it worth pushing to main/master yet?

Rate the work on a scale:

| Rating | Meaning |
|--------|---------|
| **Ship it** | Complete, tested, improves the project |
| **Ship with caveats** | Functional but has known gaps — list them |
| **Not yet** | Incomplete, broken, or needs more work — say what's missing |

Be honest. Half-finished features that break existing behavior = not yet.

## 3. How significant is this piece of work?

Classify:
- **Major**: new feature, breaking change, architectural shift, large refactor
- **Minor**: bug fix, small enhancement, config change, dependency update
- **Trivial**: formatting, typo, comment update

Then one sentence on the real-world impact: does this affect users, performance, reliability, or developer experience?

## 4. Due diligence checklist

Check each item by actually verifying, not assuming. Mark `[x]` PASS or `[ ]` SKIPPED/FAIL with a reason.

- [ ] **Tests pass** — run the test suite, report result
- [ ] **CI green** — if a PR or pushed branch exists, run `gh pr checks` (or the repo's CI status); a red required check forces **Not yet**
- [ ] **Linter clean** — run linter/formatter, report result
- [ ] **No secrets exposed** — grep changed files for `sk-`, `api_key=`, `password=`, `token=`, `secret=`, `ghp_`, `github_pat_`, `xoxb-`, `AKIA`, `npm_`, `-----BEGIN` (private keys)
- [ ] **Output validation** — if the project CLAUDE.md names an output-validation script, run it; mark N/A if the project has none
- [ ] **Build succeeds** — if frontend changes, does `next build` / `npm run build` pass?
- [ ] **Tested manually** — did we actually run the code and verify it works, or just write it?
- [ ] **No unrelated changes** — diff is clean, no accidental files or side-effect edits
- [ ] **Commit messages are clear** — do the commits tell the story of what happened?
- [ ] **Decision recorded** — if this branch chose among real alternatives, abandoned a design on evidence, or set a cross-component convention, a `docs/decisions/` record is in the diff (invoke `/record-decision`); mark N/A with "no decision record needed" if the worthiness test fails

## Output format

```
## Achievement
<bullet summary>

## Ship verdict: <Ship it | Ship with caveats | Not yet>
<one-line reasoning>

## Significance: <Major | Minor | Trivial>
<one-line impact>

## Due diligence: X/10 passed
<checklist with evidence>

## Recommendation
<what to do next — push, fix something first, or keep working>
```

## Rules

- If tests fail or secrets are exposed, verdict is **Not yet** regardless of everything else.
- If the work is incomplete (TODO comments, placeholder logic, half-implemented features), say so directly.
- Don't inflate significance to make the work feel more important than it is.
- If you didn't actually run tests or build, mark those items SKIPPED — don't pretend.

---

Target: $ARGUMENTS

If no target specified, check the current branch against the default branch.
