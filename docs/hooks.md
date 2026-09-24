# Hooks (deterministic backstops)

Per-box binding lives in `settings.json`, which git does not track. The hook is the verifier;
the prose rule still binds where the hook is blind. **Box**: `home` = this PC (Node + Python),
`work` = the work box (Python ports), `both`. Check `settings.json` before trusting a row.

| Guard | Box | Fires on | Blind spots | Escape hatch |
|---|---|---|---|---|
| Capability existence: `/name` refs get a `[CAPABILITY EXISTS]` notice (`check-skill-references.js`) | home | UserPromptSubmit | bundled skills not on disk, plugin commands, refs without a slash | none |
| Human voice: every prompt gets the `[HUMAN VOICE]` reply-shape rule plus the reply check's flags on the last reply | work | UserPromptSubmit | a reminder, not a gate | `CLAUDE_HUMAN_VOICE=off` |
| Do it properly: every prompt gets the `[DO IT PROPERLY]` rule; a bare go or continue also gets `[KEEP GOING]` | work | UserPromptSubmit | a reminder, not a gate | `CLAUDE_DO_IT_PROPERLY=off` |
| Reply check: logs counts and flags per reply (over 8 lines or 220 words, a table, 6+ bullets, a banned word, a sweeping claim, 2+ numbers with no tool call, fix-it edits with no `<diagnosis>`) to `~/.claude/state/reply_check.jsonl`; the weekly scorecard reads it | both | Stop | logs, never blocks; counts shapes, not meaning | `CLAUDE_REPLY_CHECK=off` |
| Keep going: blocks a stop once when the reply's last lines ask for a go ("say go", "shall I", "want me to", "next is X") or wait on a schedule, unless that sentence or the next names an ASK-FIRST reason, a wait on Keith's hands, or a choice between named options; logs to `~/.claude/state/keep_going.jsonl` | both | Stop | regex on the last two lines; question prompts and `/all-done`, `/grill-me` turns pass; the second stop always passes | `CLAUDE_KEEP_GOING=off` |
| Rewrite gate: denies a Write over an existing `CLAUDE.md`, `~/.claude/settings.json`, or a git-tracked file in `~/.claude`, unless the latest human prompt says "apply" | both | Write | Edit and shell writes; "apply" anywhere in the prompt passes | `CLAUDE_REWRITE_GATE=off` |
| Config sync: fetches claude-config; a clean `~/.claude` only behind `origin/main` fast-forwards, any other tree gets new skills and commands only, inside the sparse rules | both | SessionStart | never merges a dirty or diverged tree; offline skips | none |
| Commit messages: denies em dash in inline `git commit` text and PowerShell stdin pipes; `git_guard.py` (work) injects the current branch and warns on banned AI-isms | both | Bash / PowerShell | `-F <file>` messages | none |
| Backup: home copies the file to `~/.claude/backups/` (`pre-write-guard.js`); work saves one dated `.old-YYYYMMDD` copy beside it | both | Edit / Write | shell-side edits | none |
| PS 5.1 stderr: blocks `2>&1` on native exes | both | Bash / PowerShell | none | none |
| Comment budget: denies more than 3 comment lines in a row in the edit, or more than 20% comment density after the edit (15+ lines); a file already over 20% is graded on what the edit adds; skips markdown, JSON, config, `docs/`, docstrings, JSDoc | both | Edit / Write | shell writes; cannot judge WHY from WHAT | `CLAUDE_COMMENT_BUDGET=off` |
| Resource tripwire: 40+ tool calls with no Skill/Agent/Workflow gets a notice; a command matching `.claude/tripwires.json` is denied without its protocol file, and run N x every is denied until `AUDIT <sid8> #N` is in the audit file | home | UserPromptSubmit; Bash / PowerShell | regex on command text; repos without `tripwires.json` | none |
| Fable orchestrator (same script): on a Fable main thread, exec call 26+ (shell, Edit, Write, browser) since the last human message or Agent spawn is denied | home | Bash / PowerShell / Edit / Write / browser | Read, Grep, Glob and WebFetch are free; task notifications do not reset the leg | `CLAUDE_FABLE_EXEC_BUDGET=off` or a number |
| Artifact deny: `permissions.deny` lists `Artifact` and `mcp__claude_ai_Claude_Docs`, so no claude.ai page gets published | both | calls to those tools | also blocks reading or deleting an old artifact | Keith removes the entry |
| devrl episode: while this session holds a running episode lock, denies a git, npm, npx, vitest or codex command with no absolute `cd`, `-C` or `--prefix`, and git that throws away uncommitted work (checkout --, restore, reset --hard, clean -f, stash but list/show) | home | Bash | PowerShell; heredoc bodies; sub-agents only if they share the session id | `DEVRL_ALLOW_DESTRUCTIVE=1` in the command, destructive git only |
