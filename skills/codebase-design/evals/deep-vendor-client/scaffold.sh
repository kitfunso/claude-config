#!/usr/bin/env bash
set -euo pipefail
cat > vendor_client.py <<'EOF'
"""Wraps the vendor price feed: retries, backoff, and its undocumented rate limit."""
import random
import time

import requests

_tokens = {"n": 5, "last_refill": time.time()}


def _refill():
    now = time.time()
    elapsed = now - _tokens["last_refill"]
    _tokens["n"] = min(5, _tokens["n"] + elapsed * 0.5)
    _tokens["last_refill"] = now


def fetch(url: str, max_retries: int = 4) -> dict:
    """Fetch JSON from the vendor feed, respecting its undocumented rate limit."""
    for attempt in range(max_retries):
        _refill()
        if _tokens["n"] < 1:
            time.sleep(2 ** attempt + random.random())
            continue
        _tokens["n"] -= 1
        resp = requests.get(url, timeout=5)
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp.json()
    raise TimeoutError(f"rate limited after {max_retries} retries: {url}")
EOF
