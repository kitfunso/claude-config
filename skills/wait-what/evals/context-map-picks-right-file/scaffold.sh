#!/usr/bin/env bash
set -euo pipefail
mkdir -p arbs freight
cat > CONTEXT-MAP.md <<'EOF'
# Context map

- `arbs/` - crude oil arb desk. Ubiquitous language: `arbs/CONTEXT.md`.
- `freight/` - freight rate desk. Ubiquitous language: `freight/CONTEXT.md`.
EOF
cat > arbs/CONTEXT.md <<'EOF'
# Ubiquitous language (arb desk)

- MV: model value, the price the model thinks is fair for a spread.
EOF
cat > freight/CONTEXT.md <<'EOF'
# Ubiquitous language (freight desk)

- MV: minimum volume, the smallest cargo size a route will quote.
EOF
