#!/usr/bin/env bash
set -euo pipefail
printf 'def add(a, b):\n    return a - b\n' > calc.py
cat > test_calc.py <<'EOF'
import unittest
from calc import add


class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_zero(self):
        self.assertEqual(add(0, 0), 0)
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm init
printf 'def add(a, b):\n    return a + b - 1\n' > calc.py
