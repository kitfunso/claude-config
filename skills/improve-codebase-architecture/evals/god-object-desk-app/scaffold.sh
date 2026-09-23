#!/usr/bin/env bash
set -euo pipefail
cat > desk_app.py <<'EOF'
"""Everything for the Singapore gasoline desk in one file."""
import smtplib

import duckdb
import pandas as pd
import streamlit as st


class Desk:
    def __init__(self, db_path: str):
        self.con = duckdb.connect(db_path)

    def load_prices(self) -> pd.DataFrame:
        return self.con.execute("select * from prices").df()

    def compute_pnl(self, positions: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
        merged = positions.merge(prices, on="symbol")
        merged["pnl"] = (merged["mark"] - merged["cost"]) * merged["qty"]
        return merged

    def render(self):
        prices = self.load_prices()
        st.dataframe(prices)
        if st.button("Email desk head"):
            self.send_alert("Prices updated")

    def send_alert(self, msg: str):
        server = smtplib.SMTP("smtp.internal", 25)
        server.sendmail("desk@example.com", "head@example.com", msg)
        server.quit()

    def to_csv(self, df: pd.DataFrame, path: str):
        df.to_csv(path)
EOF
