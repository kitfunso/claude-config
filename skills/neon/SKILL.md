---
name: neon
description: Hand this Claude Code session over to Gemini 4 Neon now. Opens a Neon tab (Antigravity CLI) in this session's repo with a brief, and blocks Claude in this session until Keith takes it back. Use only when Keith types /neon.
disable-model-invocation: true
---

Keith wants this session to move to Neon now.

1. Run this with the Bash tool, exactly:
   `node C:/Users/skf_s/.claude/scripts/neon/handoff.mjs --here`
2. Reply with one line: the tab it opened and the brief path, or the error it printed.
3. Do no other work. After the handoff, a guard blocks Claude's tools in this session.

To take the session back later: `node C:/Users/skf_s/.claude/scripts/neon/handoff.mjs --reclaim <session id>` (the block message shows the id).
