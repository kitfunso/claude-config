# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. For trivial tasks use
judgment: these bias toward caution over speed.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- Name the readings when a request parses two ways, and say so in one line when a
  simpler approach exists. Pushing back is not a stall; asking is, unless a
  Decisiveness trigger fires.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- **If you write 200 lines and it could be 50, rewrite it.**

Stop climbing at the first rung that holds:

1. Does it need to exist? If the need is speculative, say so in one line and skip it.
2. Is it already in this codebase? Reuse it. Re-implementing what lives a few files
   over is the most common form of this mistake.
3. Standard library, native platform feature, or an already-installed dependency?
   Use it, **unless the project bans it.** `bitfall` and `fifty` both open with a
   CRITICAL handwritten-only allowlist. There this rung inverts: write it yourself.
4. Can it be one line? Then one line.
5. Only then, the smallest code that works.

The ladder shortens the solution, never the reading. Trace what a change touches
before you shorten it. The smallest change in the wrong place is a second bug.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it; don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.

The test: every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- Turn a task into a verifiable goal before starting: "add validation" becomes "write
  tests for the invalid inputs, then make them pass". State the check beside each step
  of a multi-step plan.
- Weak criteria ("make it work") force clarification rounds; strong ones let you loop
  alone.
