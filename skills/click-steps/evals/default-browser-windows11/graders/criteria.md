---
type: llm
weight: 2
---

This is a real, stable Windows 11 flow: Settings > Apps > Default apps, pick Chrome, set it as default. Pass only if all of the following hold:

1. Numbered steps, one physical action each (a single click, keystroke, or text entry per step); no step bundles two actions together.
2. Each step names the exact control in bold with the menu path (for example Settings, Apps, Default apps).
3. Opens with the entry point (where to start, for example open Settings).
4. Closes with a Verify line describing what should be visibly true once it worked.
5. Step count is in a reasonable walkthrough range, roughly 5-15 steps for this task.

Fails if the steps are written as prose paragraphs instead of a numbered list, or if it gives a registry-edit or command-line answer instead of clicks for this GUI task.
