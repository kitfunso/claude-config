---
name: commit
description: Stage, commit, and push changes fast, with the house message format and a staged-diff check. Use for 'commit this' or 'commit and push'.
---

1. Stage the files the user names (default: every changed file, staged by name). Read `git diff --staged --stat`, grep the staged diff for secrets (`sk-`, `api_key=`, `password=`), and run the project's tests and linter unless they already ran green this turn. Touch nothing else.
2. Write a `<type>: <description>` message (title under 70 chars) to a file, grep it for em dashes, and commit with `git commit -F <file>`.
3. Push to the current branch.
4. If a pre-commit hook fails, fix what it caught and commit again; use `--no-verify` only on the user's explicit ask.
