# Karpathy Guidelines

Behavioural guidelines against common LLM coding mistakes. For trivial tasks use
judgment. Thinking-before-coding lives in the global CLAUDE.md "Execution habits".

## 1. Simplicity First

**Minimum code that solves the problem. Nothing speculative.** If you write 200 lines
and it could be 50, rewrite it. Stop climbing at the first rung that holds:

1. Does it need to exist? If the need is speculative, say so in one line and skip it.
2. Is it already in this codebase? Reuse it. Re-implementing what lives a few files
   over is the most common form of this mistake.
3. Standard library, native platform feature, or an installed dependency? Use it,
   unless the project's CLAUDE.md bans it (some repos are handwritten-only; there
   this rung inverts).
4. Can it be one line? Then one line.
5. Only then, the smallest code that works.

The ladder shortens the solution, never the reading. Trace what a change touches
before you shorten it. The smallest change in the wrong place is a second bug.

## 2. Surgical Changes

**Touch only what you must. Clean up only your own mess.** Don't improve adjacent
code, comments or formatting; don't refactor what isn't broken; match existing style.
Mention unrelated dead code, don't delete it. Remove imports, variables and functions
that YOUR change made unused. Every changed line should trace to the user's request.

## 3. Goal-Driven Execution

**Define success criteria. Loop until verified.** Turn a task into a verifiable goal
before starting: "add validation" becomes "write tests for the invalid inputs, then
make them pass". State the check beside each step of a multi-step plan. Weak criteria
force clarification rounds; strong ones let you loop alone.
