#!/usr/bin/env bash
set -euo pipefail
git init -q
git checkout -q -b main
printf '# desk-tools\n' > README.md
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init repo"
git checkout -q -b feature/add-calc
cat > calc.py <<'EOF'
def add(a: float, b: float) -> float:
    return a + b
EOF
cat > test_calc.py <<'EOF'
import unittest
from calc import add


class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
EOF
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "feat: add calc.add() with test"
