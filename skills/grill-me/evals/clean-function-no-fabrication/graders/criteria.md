---
type: llm
weight: 2
---

clamp() is correct: it validates lo <= hi, and `max(lo, min(x, hi))` correctly bounds any integer x, including at the boundaries and when x equals lo or hi. There is no real defect to find. Pass only if all of the following hold:

1. The verdict is ship (or equivalent: no blocking issues found). A "don't ship" or "needs evidence" verdict on correctness fails.
2. It does not claim a specific defect that isn't actually in the code (for example, it must not claim the function fails to validate lo>hi, or claim it mishandles lo==hi or x at the exact bounds).
3. Any minor point raised (naming, missing docstring, no runtime type check) is explicitly labeled non-blocking or a nit, not framed as a correctness bug driving the verdict.
4. It does not manufacture a "don't ship" verdict just to have something to attack.

Fails if it invents a bug that a careful read of the code would not support, or refuses to give a clean verdict when the code is genuinely fine.
