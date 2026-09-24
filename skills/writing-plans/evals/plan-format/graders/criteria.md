---
type: llm
weight: 2
focus: trace
---

There is no existing P&L-by-desk page in this empty repo, so this is a genuine greenfield multi-step build. The saved plan is the content of the agent's Write call to docs/plans/ (the skill's own template text in the trace does not count); the chat reply is the agent's final message. Pass only if all of the following hold:

1. The saved plan has the required header: a title, a "REQUIRED SUB-SKILL: Use executing-plans" callout, and Goal / Architecture / Tech Stack fields.
2. Work is broken into bite-sized tasks, each with exact file paths (Create/Modify/Test) and steps in the write-test / run-to-fail / implement / run-to-pass / commit shape, not one undifferentiated block of instructions.
3. Tasks name concrete things from the request: the `pnl` table, `desk_v42.db`, a group-by-desk aggregation, a bar chart, rather than vague placeholders.
4. The chat reply announces the save location and states which execution mode was picked (subagent-driven by default, or a separate session) in one line, without presenting it to the user as an open menu of options to choose from.
5. The reply itself does not implement the working Streamlit page; code shown belongs inside the plan's task steps as illustrative snippets, not a finished feature.

Fails if the plan lacks the REQUIRED SUB-SKILL line, lacks concrete file paths, or the execution-mode choice is left as a question for the user instead of a stated default.
