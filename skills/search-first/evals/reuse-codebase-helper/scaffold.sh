#!/usr/bin/env bash
set -euo pipefail
mkdir -p lib
cat > pyproject.toml <<'EOF'
[project]
name = "desk-etl"
version = "0.1.0"
dependencies = [
    "pandas>=2.0",
    "httpx>=0.27",
]
EOF
cat > lib/retry.py <<'EOF'
"""Shared retry helper for flaky vendor calls -- reuse this, do not duplicate."""
import time
from functools import wraps


def retry_with_backoff(attempts: int = 3, base_delay: float = 0.5):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if i == attempts - 1:
                        raise
                    time.sleep(base_delay * (2 ** i))
        return wrapper
    return decorator
EOF
cat > fetch_prices.py <<'EOF'
import httpx


def fetch_price(symbol: str) -> float:
    resp = httpx.get(f"https://vendor.example/price/{symbol}")
    resp.raise_for_status()
    return resp.json()["price"]
EOF
