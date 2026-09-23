mkdir -p desk
cat > desk/reports.py <<'EOF'
import sqlite3


def fetch_trades(desk: str, conn: sqlite3.Connection):
    query = f"SELECT * FROM trades WHERE desk = '{desk}'"
    return conn.execute(query).fetchall()
EOF
