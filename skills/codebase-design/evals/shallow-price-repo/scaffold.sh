#!/usr/bin/env bash
set -euo pipefail
cat > price_repo.py <<'EOF'
"""Thin wrapper around the desk's DuckDB connection."""
import duckdb


class PriceRepo:
    def __init__(self, con: duckdb.DuckDBPyConnection):
        self.con = con

    def get_price(self, symbol: str):
        return self.con.execute(
            "select price from prices where symbol = ?", [symbol]
        ).fetchone()

    def get_all_prices(self):
        return self.con.execute("select * from prices").fetchall()

    def get_prices_since(self, date: str):
        return self.con.execute(
            "select * from prices where date >= ?", [date]
        ).fetchall()
EOF
cat > dashboard.py <<'EOF'
"""Streamlit page: renders today's prices."""
from price_repo import PriceRepo


def render(con):
    repo = PriceRepo(con)
    row = repo.get_price("MOG92SGM")
    return row
EOF
