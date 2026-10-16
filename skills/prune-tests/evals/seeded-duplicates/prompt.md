---
name: seeded-duplicates
tags: [prune-tests, needs-shell]
plugins: ["../.."]
runs: 2
max_turns: 80
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write, Skill]
---

Clean up all the useless, duplicated, redundant tests in this repo while you're at it, to make CI
quicker and have fewer tests.

Repo: the folder `setup.sh` built (a git repo on master). Commit the cut on a branch; do not push.
