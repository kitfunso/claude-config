# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Adapted from https://github.com/forrestchang/andrej-karpathy-skills. Applies globally. For trivial tasks, use judgment — these bias toward caution over speed.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- **If you write 200 lines and it could be 50, rewrite it.**

The bans above say what not to write. The ladder below says where to look first.
Stop climbing at the first rung that holds. (From github.com/dietrichgebert/ponytail,
adopted 2026-09-01, with rung 3 rewritten to defer to project law.)

1. Does it need to exist? If the need is speculative, say so in one line and skip it.
2. Is it already in this codebase? Reuse it. Re-implementing what lives a few files
   over is the most common form of this mistake.
3. Standard library, native platform feature, or an already-installed dependency?
   Use it — **unless the project bans it.** `bitfall` and `fifty` both open with a
   CRITICAL handwritten-only allowlist. There this rung inverts: write it yourself.
4. Can it be one line? Then one line.
5. Only then, the smallest code that works.

The ladder shortens the solution, never the reading. Trace what a change touches
before you shorten it. The smallest change in the wrong place is a second bug.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**Working if:** fewer unnecessary changes in diffs, fewer rewrites from overcomplication, clarifying questions come before implementation rather than after mistakes.
