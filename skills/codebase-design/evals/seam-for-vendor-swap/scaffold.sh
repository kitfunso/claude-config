#!/usr/bin/env bash
set -euo pipefail
cat > arb_calc.py <<'EOF'
"""Computes the Singapore gasoline arb spread."""
import requests


def compute_arb(cargo_size: float) -> float:
    resp = requests.get("https://vendor-a.example.com/price?sym=MOG92SGM")
    resp.raise_for_status()
    sgp_price = resp.json()["price"]

    resp2 = requests.get("https://vendor-a.example.com/price?sym=RBOB")
    resp2.raise_for_status()
    us_price = resp2.json()["price"]

    freight = 2.10
    return (sgp_price - us_price - freight) * cargo_size
EOF
