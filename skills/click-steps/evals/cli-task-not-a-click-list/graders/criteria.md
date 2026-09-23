---
type: llm
weight: 2
---

There is no GUI flow for editing arbitrary pandas code inside PyCharm; this is a code-editing task, and the skill itself says terminal and code-editing tasks get a command, not a click list. Pass only if all of the following hold:

1. It does not produce a numbered click-by-click GUI walkthrough for making this DataFrame edit (no "click File > ..." style steps for adding the column).
2. It says plainly that this is a code-editing task, not a GUI click task, rather than silently answering as if it were one.
3. It gives the actual fix as code (for example assigning `df["settlement_date"] = ...` and `df = df.dropna(subset=["settlement_date"])`), not a list of menu clicks.
4. It does not invent a fake PyCharm menu feature for "adding a DataFrame column" (no such built-in GUI feature exists).

Fails if it produces a numbered click list for the DataFrame edit itself, or fabricates a nonexistent PyCharm GUI feature.
