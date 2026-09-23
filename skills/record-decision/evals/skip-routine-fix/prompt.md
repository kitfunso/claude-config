---
name: skip-routine-fix
tags: [record-decision, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Write, Skill]
---

Fixed an off-by-one in the date-range filter in loader.py: the upper bound used `<` instead of `<=`, so the last day of each week was getting dropped. One-line change, tests pass now. Should I write a decision record for this before I ship it?
