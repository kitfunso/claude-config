#!/usr/bin/env bash
set -euo pipefail
cat > fetch.py <<'EOF'
def get_price(symbol):
    return _http_get(symbol)
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init"
cat > fetch.py <<'EOF'
import time


def get_price(symbol, retries=3):
    for attempt in range(retries):
        try:
            return _http_get(symbol)
        except ConnectionError:
            time.sleep(1)
    raise ConnectionError(f"failed to fetch {symbol} after {retries} attempts")
EOF
git add -A
