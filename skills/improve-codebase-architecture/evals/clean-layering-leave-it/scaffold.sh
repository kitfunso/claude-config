#!/usr/bin/env bash
set -euo pipefail
cat > db.py <<'EOF'
"""Read-only access to the desk's DuckDB warehouse."""
import duckdb


def get_connection(path: str = "desk.duckdb"):
    return duckdb.connect(path, read_only=True)


def load_positions(con):
    return con.execute("select * from positions").df()


def load_prices(con):
    return con.execute("select * from prices").df()
EOF
cat > pricing.py <<'EOF'
"""Pure PnL math: no I/O, no UI."""
import pandas as pd


def compute_pnl(positions: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    merged = positions.merge(prices, on="symbol")
    merged["pnl"] = (merged["mark"] - merged["cost"]) * merged["qty"]
    return merged
EOF
cat > app.py <<'EOF'
"""Streamlit entry point: wires db, pricing, and display together."""
import streamlit as st

from db import get_connection, load_positions, load_prices
from pricing import compute_pnl


def main():
    con = get_connection()
    positions = load_positions(con)
    prices = load_prices(con)
    st.dataframe(compute_pnl(positions, prices))


if __name__ == "__main__":
    main()
EOF
