---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Research Before Writing (CRITICAL for per-site fix plans)

Plans that enumerate specific call sites or other concrete code targets must READ the code before constructing the per-site mapping. Reasoning from names and line proximity is reliably wrong.

Before listing per-site fixes, grep the codebase for:

- **Existing helpers serving the same purpose.** A "new helper" that duplicates an existing one will be caught by the eng critic as DRY violation / reinvention. One `grep -r <obvious-name>` first — `resolveTenantId`, `requireAuth`, `withDb`, etc. — saves a plan-stage retry.
- **The actual call chain into each function being edited.** Don't assume from the surface command name. `cmdX` may call `api.x(ctx, id)` which calls the primitive; the per-site mapping must target the primitive's actual direct caller, not the surface command the user types.
- **Enclosing-function names by line.** Don't label a call site from line proximity to a previously-known function ("around line 2700, must be cmdResolve") — grep for `function <name>` and bound the ranges. Mislabels make execute rediscover the enclosing function instead of following the plan.
- **Same-function siblings of in-scope sites that share the same defect class.** If your fix touches sites A and B inside function F, audit F for OTHER calls that share A and B's defect class. Deferring same-function siblings while folding their neighbours is a consistency gap the review critics catch.

A plan that skips these is reliably caught at the plan-eng-critic gate and triggers a retry. The grep cost is far below the retry cost. Learned 2026-05-23 from the hippo tenant-isolation residue plan Revision 0, which made all four of these mistakes and failed plan-eng at score 58.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
```

## Remember
- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Reference relevant skills with @ syntax
- DRY, YAGNI, TDD, frequent commits

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development
- Stay in this session
- Fresh subagent per task + code review

**If Parallel Session chosen:**
- Guide them to open new session in worktree
- **REQUIRED SUB-SKILL:** New session uses superpowers:executing-plans
