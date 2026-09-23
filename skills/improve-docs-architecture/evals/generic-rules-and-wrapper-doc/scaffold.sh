#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs
cat > CLAUDE.md <<'EOF'
# Project Rules

Be helpful. Write clean code. Think step by step before acting. Use good
variable names. Avoid bugs. Communicate clearly with the user.

## Git
- Commit format: `<type>: <description>`. Title under 70 chars.
- Never force-push main without asking first.

## Deploy
See docs/RULES.md for how the pieces here fit together.
EOF
cat > docs/RULES.md <<'EOF'
# Rules

See CLAUDE.md for coding rules.
See docs/DEPLOY.md for deploy steps.
EOF
cat > docs/DEPLOY.md <<'EOF'
# Deploy

Push a tag `v*.*.*`; CI builds and ships to the VM. Rollback: redeploy the
previous tag. Desk hours only (07:00-18:00 SGT) unless it's a hotfix.
EOF
