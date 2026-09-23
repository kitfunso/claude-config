#!/usr/bin/env bash
set -euo pipefail
cat > pyproject.toml <<'EOF'
[project]
name = "desk-etl"
version = "0.1.0"
dependencies = [
    "pandas>=2.0",
    "httpx>=0.27",
    "tenacity>=8.2",
]
EOF
cat > fetch_prices.py <<'EOF'
import httpx


def fetch_price(symbol: str) -> float:
    resp = httpx.get(f"https://vendor.example/price/{symbol}")
    resp.raise_for_status()
    return resp.json()["price"]
EOF
