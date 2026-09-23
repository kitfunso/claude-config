---
type: llm
weight: 2
---

This memo is well-reasoned and benchmarked, but the benchmark only checked time and
memory, not correctness — pandas `groupby` and DuckDB `GROUP BY` handle NULL keys
differently, and the memo also says nothing about what happens if the query fails or
the CSV is malformed, or whether any other caller depends on the pandas code before
it's deleted. Any one of these is a legitimate top finding. Pass only if all of the
following hold:

1. The top-ranked finding is one real, memo-grounded gap — for example: no
   output/correctness parity check between the two engines (only time/memory were
   benchmarked), no failure-mode story for a bad or missing CSV, or no check for other
   callers of the pandas path before deleting it. Any one of these (or an equivalent
   gap actually grounded in the memo) counts; it does not have to be the
   failure-mode/caller-dependency one specifically.
2. The finding is tied to the actual memo text (quotes or closely paraphrases what it
   does or doesn't say), not invented from nowhere.
3. It gives one concrete fix matching its top finding (for example a parity diff
   between the two pipelines, naming the exception path, or checking for other
   callers).
4. It names something genuinely strong (the benchmark comparison, the unchanged
   schema/schedule) in one short, calibrated line, not generic praise.
5. It ends with a single "most important change" line.

Fails if it invents fabricated flaws about numbers not in the memo, if it praises
without being specific, or if its top finding is not grounded in the memo text.
