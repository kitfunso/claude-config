---
type: llm
weight: 2
---

calc_margin_usd is a byte-for-byte copy of calc_margin's body (same fee calc, same return expression) — Duplicated Code. Pass only if all of the following hold:

1. The Standards section names both calc_margin and calc_margin_usd and calls out the duplication.
2. It treats this as a judgement-call smell (not a hard violation, since there's no documented standard here) and suggests extracting the shared logic — describing the fix is fine; there is no file to edit in this run.
3. The Spec section says no spec/PRD is available (does not invent one).
4. Standards and Spec stay in separate labeled sections; the reply ends with a one-line summary per axis, not one merged ranking.

Fail if it doesn't notice the duplication, or if it invents a spec-compliance finding.
