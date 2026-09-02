# Karpathy Examples

Companion to `karpathy-guidelines.md`. Real code examples of what LLMs do wrong for each of the four principles, plus how to fix.

Source: https://github.com/forrestchang/andrej-karpathy-skills/blob/main/EXAMPLES.md

---

## 1. Think Before Coding

### Example 1: Hidden Assumptions

**User Request:** "Add a feature to export user data"

**Wrong — silently assumes:**

```python
def export_users(format='json'):
    users = User.query.all()
    if format == 'json':
        with open('users.json', 'w') as f:
            json.dump([u.to_dict() for u in users], f)
    elif format == 'csv':
        ...
    return f"Exported {len(users)} users"
```

Problems: assumed ALL users (privacy?), assumed file location, assumed fields, assumed CSV schema.

**Right — surface the assumptions:**

```
Before implementing, I need to clarify:
1. Scope: All users or filtered subset? (privacy)
2. Format: Browser download? Background job with email? API endpoint?
3. Fields: Which user fields? (sensitivity)
4. Volume: How many typically? (affects approach)

Simplest: API endpoint returning paginated JSON.
What's your preference?
```

### Example 2: Multiple Interpretations

**User Request:** "Make the search faster"

**Wrong — picks silently and writes 200 lines.**

**Right — name the interpretations:**

```
"Faster" could mean:
1. Response time (add indexes, cache) — 2h
2. Throughput (async, pool) — 4h
3. Perceived speed (partial results, progressive load) — 3h

Current ~500ms. Which matters most?
```

---

## 2. Simplicity First

### Example 1: Over-abstraction

**User Request:** "Add a function to calculate discount"

**Wrong:** Strategy pattern, abstract base class, config dataclass, calculator class — 30+ lines before you can compute anything.

**Right:**

```python
def calculate_discount(amount: float, percent: float) -> float:
    return amount * (percent / 100)
```

Add complexity only when multiple discount types are actually needed. Refactor then.

### Example 2: Speculative Features

**User Request:** "Save user preferences to database"

**Wrong:** PreferenceManager class with merge/validate/notify options, caching, hooks — all for "save prefs."

**Right:**

```python
def save_preferences(db, user_id: int, preferences: dict):
    db.execute(
        "UPDATE users SET preferences = ? WHERE id = ?",
        (json.dumps(preferences), user_id)
    )
```

Add caching when perf matters. Validation when bad data appears. Merging when requirement emerges.

---

## 3. Surgical Changes

### Example 1: Drive-by Refactoring

**User Request:** "Fix the bug where empty emails crash the validator"

**Wrong:** Fixes email bug AND improves email regex AND adds username length check AND adds docstrings.

**Right:** Change only the lines that handle empty emails. Nothing else.

### Example 2: Style Drift

**User Request:** "Add logging to the upload function"

**Wrong:** Adds logging AND changes single quotes to double AND adds type hints AND reformats whitespace AND changes boolean return logic.

**Right:** Add logger + log calls. Match existing quote style, no type hints if the file doesn't use them, preserve existing structure.

---

## 4. Goal-Driven Execution

### Example 1: Vague vs. Verifiable

**User Request:** "Fix the authentication system"

**Wrong:** "I'll review the code, identify issues, make improvements, and test changes." Then proceeds without clear success criteria.

**Right:**

```
"Fix authentication" — what specific issue?

If it's "users stay logged in after password change":
1. Write test: change password → verify old session invalidated
   Verify: test fails (reproduces bug)
2. Implement session invalidation on password change
   Verify: test passes
3. Edge cases: multiple sessions, concurrent changes
   Verify: additional tests pass
4. Full auth suite still green
   Verify: no regressions

Which issue are you seeing?
```

### Example 2: Multi-Step with Verification

**User Request:** "Add rate limiting to the API"

**Wrong:** 300-line commit with Redis, multiple strategies, config system, monitoring — all at once, no verification steps.

**Right:** Four independently verifiable steps:
1. In-memory limiter on one endpoint. Verify: 100 req → 10 succeed, rest 429.
2. Extract to middleware. Verify: applies to all endpoints, existing tests pass.
3. Redis backend. Verify: survives restarts, shared across instances.
4. Per-endpoint config. Verify: /search 10/min, /users 100/min.

### Example 3: Test-First Verification

**User Request:** "The sorting breaks when there are duplicate scores"

**Wrong:** Immediately change the sort key without confirming what "breaks" means.

**Right:**
1. Write a test that reproduces the bug (runs 10 times, fails with inconsistent ordering).
2. Fix using stable sort.
3. Verify test passes consistently.

---

## Anti-Patterns Summary

| Principle | Anti-Pattern | Fix |
|-----------|--------------|-----|
| Think Before Coding | Silently assumes format/fields/scope | List assumptions, ask |
| Simplicity First | Strategy pattern for one discount | One function until complexity is needed |
| Surgical Changes | Reformats quotes + adds types while fixing a bug | Change only lines that fix the reported issue |
| Goal-Driven | "I'll review and improve the code" | "Write test for bug X → make it pass → verify no regressions" |

## Key Insight

The overcomplicated examples aren't wrong in isolation — they follow real design patterns. The problem is **timing**: complexity added before it's needed makes code harder to understand, introduces more bugs, takes longer, and is harder to test.

**Good code solves today's problem simply, not tomorrow's problem prematurely.**
