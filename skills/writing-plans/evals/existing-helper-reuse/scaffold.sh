#!/usr/bin/env bash
set -euo pipefail
mkdir -p pricing views
cat > pricing/legs.py <<'EOF'
"""Shared leg-pricing helpers for every arb view."""


def resolve_leg_price(leg: str, curve: dict) -> float:
    # shared lookup used by every leg pricer -- do not duplicate this per view
    return curve.get(leg)


def compute_diff(leg_a: str, leg_b: str, curve: dict) -> float:
    return resolve_leg_price(leg_a, curve) - resolve_leg_price(leg_b, curve)
EOF
cat > views/arb_a.py <<'EOF'
from pricing.legs import resolve_leg_price


def render(curve: dict) -> float:
    return resolve_leg_price("MOG92", curve) * 7.45
EOF
cat > views/arb_b.py <<'EOF'
from pricing.legs import resolve_leg_price


def render(curve: dict) -> float:
    return resolve_leg_price("GO10", curve) - resolve_leg_price("BRT", curve)
EOF
