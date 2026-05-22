# Git Workflow

## Commit Format
`<type>: <description>`

Types: feat, fix, refactor, docs, test, chore, perf, ci

## Branch Safety
(Pre-op `git branch` check is in global CLAUDE.md.)
- NEVER force push to main/master.
- Create new commits, don't amend unless explicitly asked.
- Never skip hooks (--no-verify) unless explicitly asked.

## PR Workflow
- Analyze full commit history (not just latest commit).
- Title under 70 chars. Details in body, not title.
- Include test plan with checkboxes.

## Before Committing
- Run tests. Run linter. Check for secrets.
- Stage specific files, not `git add -A` (prevents accidental includes).
- Review diff before committing.
