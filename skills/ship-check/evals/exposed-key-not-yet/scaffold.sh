#!/usr/bin/env bash
set -euo pipefail
git init -q
git checkout -q -b main
cat > app_config.py <<'EOF'
DEBUG = False
LOG_LEVEL = "INFO"
EOF
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init app config"
git checkout -q -b feature/billing
printf '\nSTRIPE_API_KEY = "sk_%s_51NfooBarBazQuuxAAAAAAAAAAAAAAAAAAAAAAAA"\n' live >> app_config.py
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "feat: wire up billing key"
