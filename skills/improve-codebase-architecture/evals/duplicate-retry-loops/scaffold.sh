#!/usr/bin/env bash
set -euo pipefail
cat > feed_a.py <<'EOF'
"""Fetch prices from Vendor A."""
import time

import requests


def fetch_a(symbol: str) -> float:
    for attempt in range(3):
        try:
            r = requests.get(f"https://vendor-a.example/price/{symbol}", timeout=5)
            r.raise_for_status()
            return r.json()["price"]
        except requests.RequestException:
            time.sleep(2 ** attempt)
    raise TimeoutError(f"vendor A timed out for {symbol}")
EOF
cat > feed_b.py <<'EOF'
"""Fetch prices from Vendor B."""
import time

import requests


def fetch_b(symbol: str) -> float:
    for attempt in range(3):
        try:
            r = requests.get(f"https://vendor-b.example/quote/{symbol}", timeout=5)
            r.raise_for_status()
            return r.json()["last"]
        except requests.RequestException:
            time.sleep(2 ** attempt)
    raise TimeoutError(f"vendor B timed out for {symbol}")
EOF
