#!/usr/bin/env bash
set -euo pipefail
cat > CONTEXT.md <<'EOF'
# Ubiquitous language

- MV: model value, the price the model thinks is fair.
- CD: curve date, the trading day a forward curve is quoted for.
- ff-pull: the allowed drift band between MV and market before we force a re-price.
- shaping override: a manual switch that forces the arb legs to reprice immediately.
- arb leg: one side of a two-instrument spread trade.
EOF
