#!/usr/bin/env bash
set -euo pipefail
cat > loader.py <<'EOF'
"""Load the day's price file for the desk dashboard."""
import pandas as pd


def load_prices(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise e
    return df


def load_prices_safe(path: str):
    try:
        return load_prices(path)
    except:
        return None
EOF
