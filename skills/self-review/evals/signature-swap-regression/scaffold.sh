#!/usr/bin/env bash
set -euo pipefail
cat > pnl.py <<'EOF'
def calc_margin(revenue: float, cost: float) -> float:
    return revenue - cost
EOF
cat > report.py <<'EOF'
from pnl import calc_margin


def print_margin(revenue: float, cost: float) -> None:
    print(f"margin: {calc_margin(revenue, cost):.2f}")
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "feat: add margin calc and report"
cat > pnl.py <<'EOF'
def calc_margin(cost: float, revenue: float) -> float:
    return revenue - cost
EOF
