#!/usr/bin/env bash
set -euo pipefail
cat > report.py <<'EOF'
def summary(rows):
    return len(rows)
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init"
cat >> report.py <<'EOF'


def total(rows):
    return sum(r.amount for r in rows)
EOF
