#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs .github/workflows
cat > docs/INDEX.md <<'EOF'
# Docs Index

- [DEPLOY.md](DEPLOY.md): how to deploy the pricing service.
- [ONCALL.md](ONCALL.md): on-call rotation and escalation.
EOF
cat > docs/DEPLOY.md <<'EOF'
# Deploy

Push to `main`; CI runs `deploy.yml` and ships to prod automatically. Rollback:
`gh workflow run rollback.yml -f version=<tag>`.

The deploy gate (tests, lint) is enforced by CI; see
`.github/workflows/deploy.yml` for the exact checks.
EOF
cat > docs/ONCALL.md <<'EOF'
# On-call

Rotation: weekly, listed in PagerDuty. Escalate to #eng-oncall after 15
minutes of no ack.
EOF
cat > .github/workflows/deploy.yml <<'EOF'
name: deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: pytest --cov=src --cov-fail-under=85
      - run: ruff check .
      - run: ./ship.sh
EOF
