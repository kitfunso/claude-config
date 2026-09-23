#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/plans
cat > pricing.py <<'EOF'
"""Small pricing helpers for the desk sheet."""


def convert_bbl_to_mt(bbl: float, density: float) -> float:
    return bbl * density / 6.29
EOF
cat > docs/plans/2026-09-18-add-clip-price.md <<'EOF'
# Clip Price Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Add a clip_price helper so a bad tick can't push a leg price outside a sane band.

**Architecture:** One pure function in pricing.py, one unit test.

**Tech Stack:** Python, pytest.

---

### Task 1: clip_price helper

**Files:**
- Modify: `pricing.py`
- Test: `test_pricing.py`

**Step 1: Write the failing test**

```python
from pricing import clip_price

def test_clip_price_bounds():
    assert clip_price(250.0, lo=0.0, hi=200.0) == 200.0
    assert clip_price(-5.0, lo=0.0, hi=200.0) == 0.0
    assert clip_price(91.4, lo=0.0, hi=200.0) == 91.4
```

**Step 2: Run test to verify it fails**

Run: `pytest test_pricing.py -v`
Expected: FAIL with "cannot import name 'clip_price'"

**Step 3: Write minimal implementation**

```python
def clip_price(price: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, price))
```

**Step 4: Run test to verify it passes**

Run: `pytest test_pricing.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pricing.py test_pricing.py
git commit -m "feat: add clip_price bounds helper"
```
EOF
