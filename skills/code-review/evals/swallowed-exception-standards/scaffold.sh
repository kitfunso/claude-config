#!/usr/bin/env bash
set -euo pipefail
cat > CODING_STANDARDS.md <<'EOF'
# Coding standards

## Error handling
Never swallow an exception with a bare `except: pass` or `except Exception: pass`.
Always log the error or re-raise it.
EOF
cat > fetch.py <<'EOF'
import logging

logger = logging.getLogger(__name__)


def fetch(symbol: str) -> float:
    try:
        return _http_get(symbol)
    except ConnectionError:
        logger.exception("fetch failed for %s", symbol)
        raise
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init"
git tag v1
cat > fetch.py <<'EOF'
import logging
import time

logger = logging.getLogger(__name__)


def fetch(symbol: str, retries: int = 3):
    for attempt in range(retries):
        try:
            return _http_get(symbol)
        except Exception:
            time.sleep(1)
EOF
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "feat: add retry to fetch()"
