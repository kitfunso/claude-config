---
type: llm
weight: 2
---

This is a one-line bug fix with one obvious shape, not a real alternative that was weighed or a cross-component convention -- it fails the worthiness test. Pass only if all of the following hold:

1. The reply declines to write a decision record.
2. It says so explicitly (a clear "no decision record needed" or equivalent), not a silent skip.
3. Its stated reasoning matches the skill's own skip criteria: routine maintenance / straightforward bug fix / one obvious implementation shape.
4. It does not write or propose writing an ADR file for this.

Fails if it writes a decision record anyway, or the skip is implicit rather than a stated verdict.
