#!/usr/bin/env bash
set -euo pipefail
cat > discount.py <<'EOF'
"""Compute the volume discount for a cargo booking."""


def compute_discount(cargo_size_kt: float, base_rate: float) -> float:
    if cargo_size_kt >= 50:
        return base_rate * 0.95
    if cargo_size_kt >= 30:
        return base_rate * 0.98
    return base_rate
EOF
