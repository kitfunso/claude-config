#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/plans
cat > spreads.py <<'EOF'
"""Spread helpers for the desk sheet."""


def abs_spread(a: float, b: float) -> float:
    return abs(a - b)
EOF
cat > test_spreads.py <<'EOF'
from spreads import abs_spread


def test_abs_spread():
    assert abs_spread(9.5, 3.0) == 6.5
EOF
cat > docs/plans/2026-09-17-add-abs-spread.md <<'EOF'
# Absolute Spread Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Add an abs_spread helper for two-leg spread math.

**Architecture:** One pure function in spreads.py, one unit test.

**Tech Stack:** Python, pytest.

---

### Task 1: abs_spread helper

**Files:**
- Modify: `spreads.py`
- Test: `test_spreads.py`

**Step 1: Write the failing test**

```python
from spreads import abs_spread

def test_abs_spread():
    assert abs_spread(9.5, 3.0) == 6.5
```

**Step 2: Run test to verify it fails**

Run: `pytest test_spreads.py -v`
Expected: FAIL with "cannot import name 'abs_spread'"

**Step 3: Write minimal implementation**

```python
def abs_spread(a: float, b: float) -> float:
    return abs(a - b)
```

**Step 4: Run test to verify it passes**

Run: `pytest test_spreads.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add spreads.py test_spreads.py
git commit -m "feat: add abs_spread helper"
```
EOF
