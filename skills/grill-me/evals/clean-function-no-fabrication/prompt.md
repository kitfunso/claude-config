---
name: clean-function-no-fabrication
tags: [grill-me, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Grill this, find what's wrong with `clamp()` before I put it in the shared utils module:

```python
def clamp(x: int, lo: int, hi: int) -> int:
    if lo > hi:
        raise ValueError(f"lo ({lo}) > hi ({hi})")
    return max(lo, min(x, hi))
```
