---
name: commit
description: Stage, commit, and push changes with a plain message, no diff review. Use for 'commit this' or 'commit and push'.
---

1. Stage only the files the user specifies (default: all changed files); commit and push without reviewing diffs or touching anything else.
2. Write a `<type>: <description>` message (title under 70 chars) to a file, grep it for em dashes, and commit with `git commit -F <file>`.
3. Push to the current branch.
4. If a pre-commit hook fails, fix what it caught and commit again; use `--no-verify` only on the user's explicit ask.
