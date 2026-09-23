#!/usr/bin/env bash
set -euo pipefail
cat > server.py <<'EOF'
import logging

logger = logging.getLogger(__name__)


def handle_request(req):
    print("DEBUG got request", req)
    logger.info("handled request")
    return {"ok": True}
EOF
cat > requirements.txt <<'EOF'
requests==2.31.0
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init tiny service"
