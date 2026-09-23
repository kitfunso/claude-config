#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/plans
cat > pricing.py <<'EOF'
"""Small pricing helpers for the desk sheet."""


def convert_bbl_to_mt(bbl: float, density: float) -> float:
    return bbl * density / 6.29
EOF
cat > docs/plans/2026-09-19-normalize-leg.md <<'EOF'
# Normalize Leg Price Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Normalize raw leg prices before they hit the clip_price bounds check.

**Architecture:** One helper call inserted ahead of the existing bounds check.

**Tech Stack:** Python, pytest.

---

### Task 1: normalize before clipping

**Files:**
- Modify: `pricing.py`

**Step 1: Write the failing test**

```python
from pricing import normalize_and_clip

def test_normalize_and_clip():
    assert normalize_and_clip(91.4) == 91.4
```

**Step 2: Run test to verify it fails**

Run: `pytest test_pricing.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Import `normalize_leg` from `pricing/normalize.py` and use it to convert the raw leg
price before clipping, then wire it into a new `normalize_and_clip` function in
pricing.py.

**Step 4: Run test to verify it passes**

Run: `pytest test_pricing.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pricing.py
git commit -m "feat: normalize leg price before clipping"
```
EOF
