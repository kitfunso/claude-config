---
name: de-sloppify
description: "Two-pass pattern: implement, then clean up separately. Use after a large feature, complex refactor, or any substantial code change."
---

# De-Sloppify Pattern

Two focused passes beat one constrained pass. First implement, then clean up in a separate pass with fresh eyes.

## The Problem
When you ask for implementation + quality in one pass, you get neither done well. The model tries to satisfy conflicting constraints: "write fast" vs "write clean."

## The Pattern

### Pass 1: Implement
Focus only on: feature done, tests passing, logic correct. Console.log statements, commented-out code, verbose names, and defensive error handling all wait for Pass 2.

### Pass 2: De-Sloppify
Fresh review of all changes. Check for and fix:

1. **Dead code**: Remove commented-out code, unused imports, unreachable branches
2. **Debug artifacts**: Remove console.log, print(), debugger statements
3. **Test quality**: Remove tests that test the type system or framework behavior, not your code
4. **Over-engineering**: Simplify abstractions that only have one implementation
5. **Naming**: Rename vague variables (`data`, `result`, `temp`, `x`)
6. **Error handling**: Remove catch blocks that just re-throw, add handling where it's actually needed
7. **Consistency**: Match existing code style and patterns in the codebase

## Usage
After implementing a feature:
```
"Review all the changes we just made. De-sloppify: remove dead code, debug artifacts,
tests of language behavior, and over-engineering. Run the test suite after cleanup."
```

## When to Use
- After any implementation that touched 3+ files
- After a rapid prototyping session
- Before creating a PR
- After a long debugging session that left artifacts
