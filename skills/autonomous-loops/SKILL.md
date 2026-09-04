---
name: autonomous-loops
description: "Architect an autonomous claude -p loop: sequential, parallel, PR-fix, or DAG orchestration. Use for CI/CD automation design."
---

# Autonomous Loop Patterns

Six loop architectures of increasing sophistication. Pick the simplest one that fits.

## 1. Sequential Pipeline
Each step is isolated (fresh context). Order matters, exit codes propagate.

```bash
claude -p "Implement auth module per spec in PLAN.md" && \
claude -p "Review changes, fix issues, run tests" && \
claude -p "Write commit message, commit"
```

**Use when:** Simple linear tasks, each step is independent.

## 2. De-Sloppify Pipeline
Two focused agents beat one constrained agent.

```bash
claude -p "Implement feature X with full TDD"
claude -p "Review all changes. Remove: tests of language behavior, console.logs, dead code, over-engineering. Run test suite."
```

**Use when:** Any implementation task. Always follow implementation with cleanup.

## 3. Parallel Generation
Spawn N agents with different creative directions. Each gets an iteration number to prevent duplicates.

```bash
for i in $(seq 1 5); do
  claude -p "Iteration $i: Generate solution for X. Be creative, try approach $i." &
done
wait
claude -p "Review all 5 solutions in output/. Pick the best, explain why."
```

**Use when:** Creative/exploratory tasks where multiple approaches might work.

## 4. Continuous PR Loop
Agent runs in a loop: create PR → wait for CI → fix failures → repeat.

Key elements:
- `SHARED_TASK_NOTES.md` bridges context gaps between iterations
- Auto-fix failing CI checks
- Configurable max-runs, max-cost, completion signals
- Merge queue with conflict recovery

**Use when:** Automated PR workflows, CI-driven development.

## 5. Spec-Driven DAG Orchestration
Most sophisticated: decompose spec into tiered work units with dependency DAG.

- Each unit runs through quality pipeline in isolated worktree
- Separate context windows per stage (reviewer ≠ author)
- Merge queue with eviction recovery

**Use when:** Large features with multiple interdependent components.

## Failure Modes to Watch
- Loop churn without measurable progress → freeze, audit, reduce scope
- Repeated retries with same root cause → investigate, don't retry
- Merge queue stalls → check for dependency cycles
- Cost drift from unbounded escalation → set `--max-budget-usd`
