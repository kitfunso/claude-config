---
name: eval-driven-dev
description: "Eval-Driven Development: evals as unit tests for AI work. Use for AI workflows, agent pipelines, or prompt engineering quality checks."
---

# Eval-Driven Development

Evals are unit tests for AI development. Define success criteria BEFORE implementing, measure AFTER.

## Two Eval Types

### Capability Evals — Does the new thing work?
```markdown
[CAPABILITY EVAL: feature-name]
Success Criteria:
  - [ ] Criterion 1 (objectively verifiable)
  - [ ] Criterion 2
  - [ ] Criterion 3
```

### Regression Evals — Did we break anything?
```markdown
[REGRESSION EVAL: feature-name]
Existing Behavior:
  - test-1: PASS/FAIL
  - test-2: PASS/FAIL
```

## Grader Types

| Type | When | How |
|------|------|-----|
| **Code-based** | Deterministic outputs | grep patterns, run tests, build checks, file existence |
| **Model-based** | Open-ended outputs | Claude evaluates against rubric (use separate context) |
| **Human-based** | Subjective quality | Flag for manual review |

## Metrics

- **pass@k** — "At least one success in k attempts." Target: pass@3 > 90%
- **pass^k** — "All k trials succeed." Higher bar for critical paths.

## Workflow

1. **Define** evals BEFORE coding (what does success look like?)
2. **Implement** the feature
3. **Evaluate** — run evals, collect pass rates
4. **Iterate** — fix failures, re-evaluate
5. **Report** — document final pass rates with the change

## Key Insight
The reviewer/grader should be a SEPARATE context from the implementer. Author bias means the implementer will rate their own work too favorably. Use a subagent or separate pass for grading.
