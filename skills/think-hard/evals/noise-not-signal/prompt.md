---
name: noise-not-signal
tags: [think-hard, noise, ro]
plugins: ["../.."]
runs: 3
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

We trimmed our team's coding-assistant config file from 313 lines to 145 on 13 September. Here is the weekly share of my messages that were corrections ("wrong", "why did you", "wtf"), across every session on this machine:

- week of 08-17: 18.1% (n=210)
- week of 08-24: 19.6% (n=184)
- week of 08-31: 17.2% (n=163)
- week of 09-07: 20.3% (n=133)
- week of 09-14: 9.2% (n=120)
- week of 09-21: 17.0% (n=153, three days so far, 96 of the 153 from one session)

Think hard: did the trim degrade the assistant's performance?
