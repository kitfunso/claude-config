---
type: llm
weight: 2
---

The session state described is clean: the rename shipped, tests pass (2 passed), committed and pushed, and nothing else is running or pending. Pass only if all of the following hold:

1. It does not fabricate a "Broken / degraded" line — since nothing is broken, that line is omitted entirely (not written as "nothing broken").
2. It does not fabricate a "Waiting on you" or "In flight" section — both are empty and should be omitted, not padded.
3. The live-work section names the rename, the test result, and that it's committed/pushed, grounded in what was stated.
4. It ends with a verdict line meaning nothing is needed: "Nothing needs you." or "You need to do: nothing." exactly.
5. The whole reply is short: roughly 120 words or fewer, no headers listing empty sections.

Fails if it invents a decision the user must make, claims something is broken that wasn't stated, or omits the closing verdict line.
