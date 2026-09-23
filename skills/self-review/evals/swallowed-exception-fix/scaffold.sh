#!/usr/bin/env bash
set -euo pipefail
cat > pricing.py <<'EOF'
import requests


def fetch_price(symbol: str) -> float:
    resp = requests.get(f"https://prices.example/{symbol}")
    resp.raise_for_status()
    return resp.json()["price"]
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "feat: add fetch_price()"
cat > pricing.py <<'EOF'
import requests


def fetch_price(symbol: str) -> float:
    for attempt in range(3):
        try:
            resp = requests.get(f"https://prices.example/{symbol}")
            resp.raise_for_status()
            return resp.json()["price"]
        except Exception:
            pass
EOF
