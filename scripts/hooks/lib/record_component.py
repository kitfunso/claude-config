"""Shared writer for component_outcomes, the Python twin of record-component.js.

Every .py hook's deny path goes through here. Never raises: recording must not
change what the caller was going to do.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[3] / "dev-framework" / "episodes.db"


def record(
    *,
    kind: str,
    name: str,
    session_id: str | None = None,
    cwd: str | None = None,
    blocked: bool = False,
    notes: str | None = None,
) -> None:
    try:
        if not kind or not name:
            return
        db = Path(os.environ.get("DEVRL_DB") or DEFAULT_DB)
        if not db.is_file():  # opening a missing file would create an empty db in any repo
            return
        conn = sqlite3.connect(db, timeout=3)
        try:
            conn.execute(
                "INSERT INTO component_outcomes "
                "(kind, name, session_id, invoked_at, blocked, cwd, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(kind),
                    str(name),
                    session_id,
                    datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                    1 if blocked else 0,
                    cwd,
                    str(notes)[:500] if notes else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass
