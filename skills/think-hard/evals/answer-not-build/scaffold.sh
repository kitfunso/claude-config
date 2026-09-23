#!/usr/bin/env bash
set -euo pipefail
cat > db.py <<'EOF'
"""Read-only access to the versioned desk database."""
import sqlite3
from pathlib import Path

POINTER = Path("current.txt")


def current_version() -> str:
    # the publisher swaps this pointer to a new file after every ETL run
    return POINTER.read_text().strip()


def load(sql: str) -> list[tuple]:
    con = sqlite3.connect(f"file:{current_version()}?mode=ro", uri=True)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()
EOF
printf 'desk_v42.db\n' > current.txt
