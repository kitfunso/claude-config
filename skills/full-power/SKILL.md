---
name: full-power
description: Maximize agent capability by spawning well-briefed sub-agents, using every available resource, and verifying everything before acceptance. Use when tackling complex or high-stakes tasks that demand thoroughness.
---

# Full Power Mode

You are now operating in full-power mode. Follow these directives strictly.

**What this mode is NOT:** a license to skip rigor. The mandatory gates in global
CLAUDE.md still run first — the Root Cause `<diagnosis>` pass, `<cost-calculus>` on
patch-vs-structural forks, and Outside Voice review for multi-step plans. Full power
accelerates execution AFTER those gates, never around them.

## Sub-Agents — Brief Well, Verify Always

**Spawn liberally**, but every sub-agent must be briefed AND reviewed. No exceptions.

**Model routing (binding):** always set `model` explicitly — `sonnet` by default;
`opus` only on explicit ask or a genuinely hard verify/review stage; never `fable`
for fan-outs (directive 2026-07-20 + global CLAUDE.md subagent routing). Full power
means more agents, not more expensive ones.

### Briefing (prevents drift)

Before calling any `Agent` tool, write a prompt that includes ALL of the following:

1. **Goal + why** — what the user is trying to accomplish and why it matters. One sentence.
2. **Exact scope** — what the agent MUST do, and explicitly what it MUST NOT do
   (no refactors, no unrelated fixes, no new files unless asked).
3. **Concrete anchors** — file paths with line numbers, function/symbol names, exact
   commands to run. No vague "find the relevant code."
4. **Context already gathered** — what you've ruled out, what you've tried, what's
   been confirmed. Prevents re-investigation.
5. **Non-negotiables** — the project CLAUDE.md mandates that apply. Read them from the
   project's CLAUDE.md THIS session and quote the relevant ones into the brief — don't
   recall them from memory, and don't assume the agent will load them itself.
6. **Deliverable shape** — exactly what to return: a diff, a ≤200-word report, a file
   path, a pass/fail verdict. Cap the response length.
7. **Stop conditions** — when to stop and report vs. when to keep going. Prevents
   runaway work.

Terse prompts → shallow work. If your prompt is under 5 sentences for a non-trivial
task, it's probably under-briefed.

**Never delegate understanding.** Do not write "based on your findings, fix it" or
"do what's needed." Synthesis stays with you. The agent executes specifics.

### Review (catches drift)

After every sub-agent returns, BEFORE acting on its output or reporting success:

1. **Read the actual artifacts it produced** — diffs, files, command output. Don't
   trust the summary alone.
2. **Check against the brief** — did it stay in scope? Did it touch files it
   shouldn't have? Did it introduce new abstractions, refactors, or helpers not
   requested?
3. **Verify claims** — if the agent says "tests pass" or "validation succeeded," run
   the command yourself or read the log.
4. **Check for slop** — backwards-compat shims, unused `_vars`, placeholder TODOs,
   unnecessary error handling, over-engineered abstractions, docstrings/comments
   explaining the obvious.
5. **Check project non-negotiables** — did it violate any of the CLAUDE.md mandates
   you briefed it on?
6. **If drift is detected:** send a corrective `SendMessage` to the same agent naming
   the specific violations and the fix — it still holds the context, so correcting it
   is cheaper than redoing the work yourself. Do NOT silently clean up its mess.

If the agent's output is trustworthy and in-scope, proceed. If not, reject and re-run
with tighter constraints.

### Parallelism & orchestration

- Run truly independent agents concurrently in a single message.
- Do NOT parallelize when one agent's output is needed to brief another — that's
  sequential.
- Pick the right agent type for each subtask (table in
  `~/.claude/rules/agent-routing.md` — read it, don't recall it).
- Invoking this skill authorizes the `Workflow` tool when the task genuinely needs
  deterministic fan-out (loops, adversarial verify, large sweeps). Same rules apply
  inside a workflow: full briefs, sonnet-default model overrides on every `agent()`
  call, review the outputs.

## Resources

- Use every tool at your disposal: connected MCP servers, web search, browser, LSP,
  skills.
- Prefer the most authoritative source for each question: official docs for library
  APIs, `git log`/`git blame` for history, the live DB/read-model for data state, the
  code itself over memory.
- Before recommending a file/function/flag from memory, verify it still exists.

## Rigor

- **Think hard.** Reason through edge cases, failure modes, and second-order effects
  before acting.
- **Verify everything.** Read before editing. Test after changing. Cross-check numbers
  against multiple sources.
- Double-check critical operations: SQL, production scripts, data syncs, destructive
  commands, anything touching prod or master.
- If uncertain, investigate first. Do not guess.

## Execution

- Break complex tasks into discrete steps with `TodoWrite`. Mark each done as soon as
  it finishes — don't batch.
- Validate outputs at each stage before moving to the next.
- Before claiming completion: run the project's verification command (tests, build,
  type-check, validation script) and confirm output. Evidence before assertions.
- If two iterations fail on the same problem, stop and report honestly instead of
  burning tokens.
